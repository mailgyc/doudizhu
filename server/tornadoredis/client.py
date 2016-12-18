# -*- coding: utf-8 -*-
import collections
import datetime
import logging
import sys
import time as mod_time
import weakref
from collections import namedtuple, deque
from functools import partial

from tornado import gen
from tornado import stack_context
from tornado.escape import to_unicode, to_basestring
from tornado.ioloop import IOLoop

from .connection import Connection
from .exceptions import RequestError, ConnectionError, ResponseError

log = logging.getLogger('tornadoredis.client')

Message = namedtuple('Message', ('kind', 'channel', 'body', 'pattern'))
GeoData = namedtuple('GeoData', ('member', 'dist', 'coords', 'hash'))

PY3 = sys.version > '3'


class CmdLine(object):
    def __init__(self, cmd, *args, **kwargs):
        self.cmd = cmd
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        return self.cmd + '(' + str(self.args) + ',' + str(self.kwargs) + ')'


def string_keys_to_dict(key_string, callback):
    return dict([(key, callback) for key in key_string.split()])


def dict_merge(*dicts):
    merged = {}
    for d in dicts:
        merged.update(d)
    return merged


def reply_to_bool(r, *args, **kwargs):
    return bool(r)


def make_reply_assert_msg(msg):
    def reply_assert_msg(r, *args, **kwargs):
        return r == msg

    return reply_assert_msg


def reply_set(r, *args, **kwargs):
    return set(r)


def reply_dict_from_pairs(r, *args, **kwargs):
    return dict(list(zip(r[::2], r[1::2])))


def reply_str(r, *args, **kwargs):
    return r or ''


def reply_int(r, *args, **kwargs):
    return int(r) if r is not None else None


def reply_number(r, *args, **kwargs):
    if r is not None:
        num = float(r)
        if not num.is_integer():
            return num
        else:
            return int(num)
    return None


def reply_datetime(r, *args, **kwargs):
    return datetime.datetime.fromtimestamp(int(r))


def reply_pubsub_message(r, *args, **kwargs):
    """
    Handles a Pub/Sub message and packs its data into a Message object.
    """
    if len(r) == 3:
        (kind, channel, body) = r
        pattern = channel
    elif len(r) == 4:
        (kind, pattern, channel, body) = r
    elif len(r) == 2:
        (kind, channel) = r
        body = pattern = None
    else:
        raise ValueError('Invalid number of arguments')
    return Message(kind, channel, body, pattern)


def reply_zset(r, *args, **kwargs):
    if r and 'WITHSCORES' in args:
        return reply_zset_withscores(r, *args, **kwargs)
    else:
        return r


def reply_zset_withscores(r, *args, **kwargs):
    return list(zip(r[::2], list(map(reply_number, r[1::2]))))


def reply_hmget(r, key, *fields, **kwargs):
    return dict(list(zip(fields, r)))


def reply_info(response, *args):
    info = {}

    def get_value(value):
        # Does this string contain subvalues?
        if (',' not in value) or ('=' not in value):
            return value
        sub_dict = {}
        for item in value.split(','):
            k, v = item.split('=')
            try:
                sub_dict[k] = int(v)
            except ValueError:
                sub_dict[k] = v
        return sub_dict

    for line in response.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split(':')
            try:
                info[key] = int(value)
            except ValueError:
                info[key] = get_value(value)
    return info


def reply_ttl(r, *args, **kwargs):
    return r != -1 and r or None


def reply_map(*funcs):
    def reply_fn(r, *args, **kwargs):
        if len(funcs) != len(r):
            raise ValueError('more results than functions to map')
        return [f(part) for f, part in zip(funcs, r)]

    return reply_fn


def reply_coords(r, *args, **kwargs):
    return [(float(c[0]), float(c[1])) for c in r]


def reply_geo_radius(r, *args, **kwargs):
    geo_data = []
    for member in r:
        name = member[0]
        dist = coords = hs = None

        if 'WITHDIST' in args:
            dist = float(member[1])

        if 'WITHHASH' in args and 'WITHDIST' in args:
            hs = int(member[2])
        elif 'WITHHASH' in args:
            hs = int(member[1])

        if 'WITHCOORD' in args and 'WITHHASH' in args and 'WITHDIST' in args:
            coords = (float(member[3][0]), float(member[3][1]))
        elif 'WITHCOORD' in args and ('WITHHASH' in args or 'WITHDIST' in args):
            coords = (float(member[2][0]), float(member[2][1]))
        elif 'WITHCOORD' in args:
            coords = (float(member[1][0]), float(member[1][1]))

        geo_data.append(GeoData(name, dist, coords, hs))
    return geo_data


def to_list(source):
    if isinstance(source, str):
        return [source]
    else:
        return list(source)


PUB_SUB_COMMANDS = (
    'SUBSCRIBE',
    'PSUBSCRIBE',
    'UNSUBSCRIBE',
    'PUNSUBSCRIBE',
    # Not a command at all
    'LISTEN',
)

REPLY_MAP = dict_merge(
    string_keys_to_dict('AUTH BGREWRITEAOF BGSAVE DEL EXISTS '
                        'EXPIRE HDEL HEXISTS '
                        'HMSET MOVE PERSIST RENAMENX SISMEMBER SMOVE '
                        'SETEX SAVE SETNX MSET',
                        reply_to_bool),
    string_keys_to_dict('BITCOUNT DECRBY GETBIT HLEN INCRBY LINSERT '
                        'LPUSHX RPUSHX SADD SCARD SDIFFSTORE SETBIT SETRANGE '
                        'SINTERSTORE STRLEN SUNIONSTORE SETRANGE',
                        reply_int),
    string_keys_to_dict('FLUSHALL FLUSHDB SELECT SET SETEX '
                        'SHUTDOWN RENAME RENAMENX WATCH UNWATCH',
                        make_reply_assert_msg('OK')),
    string_keys_to_dict('SMEMBERS SINTER SUNION SDIFF',
                        reply_set),
    string_keys_to_dict('HGETALL BRPOP BLPOP',
                        reply_dict_from_pairs),
    string_keys_to_dict('HGET',
                        reply_str),
    string_keys_to_dict('SUBSCRIBE UNSUBSCRIBE LISTEN '
                        'PSUBSCRIBE UNSUBSCRIBE',
                        reply_pubsub_message),
    string_keys_to_dict('ZRANK ZREVRANK',
                        reply_int),
    string_keys_to_dict('ZCOUNT ZCARD',
                        reply_int),
    string_keys_to_dict('ZRANGE ZRANGEBYSCORE ZREVRANGE '
                        'ZREVRANGEBYSCORE',
                        reply_zset),
    string_keys_to_dict('ZSCORE ZINCRBY',
                        reply_number),
    string_keys_to_dict('SCAN HSCAN SSCAN',
                        reply_map(reply_int, reply_set)),
    string_keys_to_dict('GEODIST',
                        reply_number),
    string_keys_to_dict('GEOPOS',
                        reply_coords),
    string_keys_to_dict('GEORADIUS GEORADIUSBYMEMBER',
                        reply_geo_radius),
    {'HMGET': reply_hmget,
     'PING': make_reply_assert_msg('PONG'),
     'LASTSAVE': reply_datetime,
     'TTL': reply_ttl,
     'INFO': reply_info,
     'MULTI_PART': make_reply_assert_msg('QUEUED'),
     'TIME': lambda x: (int(x[0]), int(x[1])),
     'ZSCAN': reply_map(reply_int, reply_zset_withscores)}
)


class Client(object):
    #    __slots__ = ('_io_loop', '_connection_pool', 'connection', 'subscribed',
    #                 'password', 'selected_db', '_pipeline', '_weak')

    def __init__(self, host='localhost', port=6379, unix_socket_path=None,
                 password=None, selected_db=None, io_loop=None,
                 connection_pool=None):
        self._io_loop = io_loop or IOLoop.current()
        self._connection_pool = connection_pool
        self._weak = weakref.proxy(self)
        if connection_pool:
            connection = (connection_pool
                          .get_connection(event_handler_ref=self._weak))
        else:
            connection = Connection(host=host, port=port,
                                    unix_socket_path=unix_socket_path,
                                    event_handler_proxy=self._weak,
                                    io_loop=self._io_loop)
        self.connection = connection
        self.subscribed = set()
        self.subscribe_callbacks = deque()
        self.unsubscribe_callbacks = []
        self.password = password
        self.selected_db = selected_db or 0
        self._pipeline = None

    def __del__(self):
        try:
            connection = self.connection
            pool = self._connection_pool
        except AttributeError:
            connection = None
            pool = None
        if connection:
            if pool:
                pool.release(connection)
                connection.wait_until_ready()
            else:
                connection.disconnect()

    def __repr__(self):
        return 'tornadoredis.Client (db=%s)' % (self.selected_db)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass

    def __getattribute__(self, item):
        """
        Bind methods to the weak proxy to avoid memory leaks
        when bound method is passed as argument to the gen.Task
        constructor.
        """
        a = super(Client, self).__getattribute__(item)
        try:
            if isinstance(a, collections.Callable) and a.__self__:
                try:
                    a = self.__class__.__dict__[item]
                except KeyError:
                    a = Client.__dict__[item]
                a = partial(a, self._weak)
        except AttributeError:
            pass
        return a

    def pipeline(self, transactional=False):
        """
        Creates the 'Pipeline' to send multiple redis commands
        in a single request.

        Usage:
            pipe = self.client.pipeline()
            pipe.hset('foo', 'bar', 1)
            pipe.expire('foo', 60)

            yield gen.Task(pipe.execute)

        or:

            with self.client.pipeline() as pipe:
                pipe.hset('foo', 'bar', 1)
                pipe.expire('foo', 60)

                yield gen.Task(pipe.execute)
        """
        if not self._pipeline:
            self._pipeline = Pipeline(
                transactional=transactional,
                selected_db=self.selected_db,
                password=self.password,
                io_loop=self._io_loop,
            )
            self._pipeline.connection = self.connection
        return self._pipeline

    def on_disconnect(self):
        if self.subscribed:
            self.subscribed = set()
        raise ConnectionError("Socket closed on remote end")

    #### connection
    def connect(self):
        if not self.connection.connected():
            pool = self._connection_pool
            if pool:
                old_conn = self.connection
                self.connection = pool.get_connection(event_handler_ref=self)
                self.connection.ready_callbacks = old_conn.ready_callbacks
            else:
                self.connection.connect()

    @gen.engine
    def disconnect(self, callback=None):
        """
        Disconnects from the Redis server.
        """
        connection = self.connection
        if connection:
            pool = self._connection_pool
            if pool:
                pool.release(connection)
                yield gen.Task(connection.wait_until_ready)
                proxy = pool.make_proxy(client_proxy=self._weak,
                                        connected=False)
                self.connection = proxy
            else:
                self.connection.disconnect()
        if callback:
            callback(False)

    #### formatting
    def encode(self, value):
        if not isinstance(value, str):
            if not PY3 and isinstance(value, str):
                value = value.encode('utf-8')
            else:
                value = str(value)
        if PY3:
            value = value.encode('utf-8')
        return value

    def format_command(self, *tokens, **kwargs):
        cmds = []
        for t in tokens:
            e_t = self.encode(t)
            e_t_s = to_basestring(e_t)
            cmds.append('$%s\r\n%s\r\n' % (len(e_t), e_t_s))
        return '*%s\r\n%s' % (len(tokens), ''.join(cmds))

    def format_reply(self, cmd_line, data):
        if cmd_line.cmd not in REPLY_MAP:
            return data
        try:
            res = REPLY_MAP[cmd_line.cmd](data,
                                          *cmd_line.args,
                                          **cmd_line.kwargs)
        except Exception as e:
            raise ResponseError(
                'failed to format reply to %s, raw data: %s; err message: %s'
                % (cmd_line, data, e), cmd_line
            )
        return res

    ####

    @gen.engine
    def execute_command(self, cmd, *args, **kwargs):
        result = None
        execute_pending = cmd not in ('AUTH', 'SELECT')

        callback = kwargs.get('callback', None)
        if 'callback' in kwargs:
            del kwargs['callback']
        cmd_line = CmdLine(cmd, *args, **kwargs)
        if callback and self.subscribed and cmd not in PUB_SUB_COMMANDS:
            callback(RequestError(
                'Executing non-Pub/Sub command while in subscribed state',
                cmd_line))
            return

        n_tries = 2
        while n_tries > 0:
            n_tries -= 1
            if not self.connection.connected():
                self.connection.connect()

            if not self.subscribed and not self.connection.ready():
                yield gen.Task(self.connection.wait_until_ready)

            if not self.subscribed and cmd not in ('AUTH', 'SELECT'):
                if self.password and self.connection.info.get('pass', None) != self.password:
                    yield gen.Task(self.auth, self.password)
                if self.selected_db and self.connection.info.get('db', 0) != self.selected_db:
                    yield gen.Task(self.select, self.selected_db)

            command = self.format_command(cmd, *args, **kwargs)
            try:
                yield gen.Task(self.connection.write, command)
            except Exception as e:
                self.connection.disconnect()
                if not n_tries:
                    raise e
                else:
                    continue

            listening = ((cmd in PUB_SUB_COMMANDS) or
                         (self.subscribed and cmd == 'PUBLISH'))
            if listening:
                result = True
                execute_pending = False
                break
            else:
                result = None
                data = yield gen.Task(self.connection.readline)
                if not data:
                    if not n_tries:
                        raise ConnectionError('no data received')
                else:
                    resp = self.process_data(data, cmd_line)
                    if isinstance(resp, partial):
                        resp = yield gen.Task(resp)
                    result = self.format_reply(cmd_line, resp)
                    break

        if execute_pending:
            self.connection.execute_pending_command()

        if callback:
            callback(result)

    @gen.engine
    def _consume_bulk(self, tail, callback=None):
        response = yield gen.Task(self.connection.read, int(tail) + 2)
        if isinstance(response, Exception):
            raise response
        if not response:
            raise ResponseError('EmptyResponse')
        else:
            response = to_unicode(response)
            response = response[:-2]
        callback(response)

    def process_data(self, data, cmd_line):
        data = to_basestring(data)
        data = data[:-2]  # strip \r\n

        if data == '$-1':
            response = None
        elif data == '*0' or data == '*-1':
            response = []
        else:
            head, tail = data[0], data[1:]

            if head == '*':
                return partial(self.consume_multibulk, int(tail), cmd_line)
            elif head == '$':
                return partial(self._consume_bulk, tail)
            elif head == '+':
                response = tail
            elif head == ':':
                response = int(tail)
            elif head == '-':
                if tail.startswith('ERR'):
                    tail = tail[4:]
                response = ResponseError(tail, cmd_line)
            else:
                raise ResponseError('Unknown response type %s' % head,
                                    cmd_line)
        return response

    @gen.engine
    def consume_multibulk(self, length, cmd_line, callback=None):
        tokens = []
        while len(tokens) < length:
            data = yield gen.Task(self.connection.readline)
            if not data:
                raise ResponseError(
                    'Not enough data in response to %s, accumulated tokens: %s'
                    % (cmd_line, tokens),
                    cmd_line)
            token = self.process_data(data, cmd_line)
            if isinstance(token, partial):
                token = yield gen.Task(token)
            tokens.append(token)

        callback(tokens)

    ### MAINTENANCE
    def bgrewriteaof(self, callback=None):
        self.execute_command('BGREWRITEAOF', callback=callback)

    def dbsize(self, callback=None):
        self.execute_command('DBSIZE', callback=callback)

    def flushall(self, callback=None):
        self.execute_command('FLUSHALL', callback=callback)

    def flushdb(self, callback=None):
        self.execute_command('FLUSHDB', callback=callback)

    def ping(self, callback=None):
        self.execute_command('PING', callback=callback)

    def object(self, infotype, key, callback=None):
        self.execute_command('OBJECT', infotype, key, callback=callback)

    def info(self, section_name=None, callback=None):
        args = ('INFO',)
        if section_name:
            args += (section_name,)
        self.execute_command(*args, callback=callback)

    def echo(self, value, callback=None):
        self.execute_command('ECHO', value, callback=callback)

    def time(self, callback=None):
        """
        Returns the server time as a 2-item tuple of ints:
        (seconds since epoch, microseconds into this second).
        """
        self.execute_command('TIME', callback=callback)

    def select(self, db, callback=None):
        self.selected_db = db
        if self.connection.info.get('db', None) != db:
            self.connection.info['db'] = db
            self.execute_command('SELECT', '%s' % db, callback=callback)
        elif callback:
            callback(True)

    def shutdown(self, callback=None):
        self.execute_command('SHUTDOWN', callback=callback)

    def save(self, callback=None):
        self.execute_command('SAVE', callback=callback)

    def bgsave(self, callback=None):
        self.execute_command('BGSAVE', callback=callback)

    def lastsave(self, callback=None):
        self.execute_command('LASTSAVE', callback=callback)

    def keys(self, pattern='*', callback=None):
        self.execute_command('KEYS', pattern, callback=callback)

    def auth(self, password, callback=None):
        self.password = password
        if self.connection.info.get('pass', None) != password:
            self.connection.info['pass'] = password
            self.execute_command('AUTH', password, callback=callback)
        elif callback:
            callback(True)

    ### BASIC KEY COMMANDS
    def append(self, key, value, callback=None):
        self.execute_command('APPEND', key, value, callback=callback)

    def getrange(self, key, start, end, callback=None):
        """
        Returns the substring of the string value stored at ``key``,
        determined by the offsets ``start`` and ``end`` (both are inclusive)
        """
        self.execute_command('GETRANGE', key, start, end, callback=callback)

    def expire(self, key, ttl, callback=None):
        self.execute_command('EXPIRE', key, ttl, callback=callback)

    def expireat(self, key, when, callback=None):
        """
        Sets an expire flag on ``key``. ``when`` can be represented
        as an integer indicating unix time or a Python datetime.datetime object.
        """
        if isinstance(when, datetime.datetime):
            when = int(mod_time.mktime(when.timetuple()))
        self.execute_command('EXPIREAT', key, when, callback=callback)

    def ttl(self, key, callback=None):
        self.execute_command('TTL', key, callback=callback)

    def type(self, key, callback=None):
        self.execute_command('TYPE', key, callback=callback)

    def randomkey(self, callback=None):
        self.execute_command('RANDOMKEY', callback=callback)

    def rename(self, src, dst, callback=None):
        self.execute_command('RENAME', src, dst, callback=callback)

    def renamenx(self, src, dst, callback=None):
        self.execute_command('RENAMENX', src, dst, callback=callback)

    def move(self, key, db, callback=None):
        self.execute_command('MOVE', key, db, callback=callback)

    def persist(self, key, callback=None):
        self.execute_command('PERSIST', key, callback=callback)

    def pexpire(self, key, time, callback=None):
        """
        Set an expire flag on key ``key`` for ``time`` milliseconds.
        ``time`` can be represented by an integer or a Python timedelta
        object.
        """
        if isinstance(time, datetime.timedelta):
            ms = int(time.microseconds / 1000)
            time = time.seconds + time.days * 24 * 3600 * 1000 + ms
        self.execute_command('PEXPIRE', key, time, callback=callback)

    def pexpireat(self, key, when, callback=None):
        """
        Set an expire flag on key ``key``. ``when`` can be represented
        as an integer representing unix time in milliseconds (unix time * 1000)
        or a Python datetime.datetime object.
        """
        if isinstance(when, datetime.datetime):
            ms = int(when.microsecond / 1000)
            when = int(mod_time.mktime(when.timetuple())) * 1000 + ms
        self.execute_command('PEXPIREAT', key, when, callback=callback)

    def pttl(self, key, callback=None):
        "Returns the number of milliseconds until the key will expire"
        self.execute_command('PTTL', key, callback=callback)

    def substr(self, key, start, end, callback=None):
        self.execute_command('SUBSTR', key, start, end, callback=callback)

    def delete(self, *keys, **kwargs):
        self.execute_command('DEL', *keys, callback=kwargs.get('callback'))

    def set(self, key, value, expire=None, pexpire=None,
            only_if_not_exists=False, only_if_exists=False, callback=None):
        args = []
        if expire is not None:
            args.extend(("EX", expire))
        if pexpire is not None:
            args.extend(("PX", pexpire))
        if only_if_not_exists and only_if_exists:
            raise ValueError("only_if_not_exists and only_if_exists "
                             "cannot be true simultaneously")
        if only_if_not_exists:
            args.append("NX")
        if only_if_exists:
            args.append("XX")

        self.execute_command('SET', key, value, *args, callback=callback)

    def setex(self, key, ttl, value, callback=None):
        self.execute_command('SETEX', key, ttl, value, callback=callback)

    def setnx(self, key, value, callback=None):
        self.execute_command('SETNX', key, value, callback=callback)

    def setrange(self, key, offset, value, callback=None):
        self.execute_command('SETRANGE', key, offset, value, callback=callback)

    def strlen(self, key, callback=None):
        self.execute_command('STRLEN', key, callback=callback)

    def mset(self, mapping, callback=None):
        items = [i for k, v in list(mapping.items()) for i in (k, v)]
        self.execute_command('MSET', *items, callback=callback)

    def msetnx(self, mapping, callback=None):
        items = [i for k, v in list(mapping.items()) for i in (k, v)]
        self.execute_command('MSETNX', *items, callback=callback)

    def get(self, key, callback=None):
        self.execute_command('GET', key, callback=callback)

    def mget(self, keys, callback=None):
        self.execute_command('MGET', *keys, callback=callback)

    def getset(self, key, value, callback=None):
        self.execute_command('GETSET', key, value, callback=callback)

    def exists(self, key, callback=None):
        self.execute_command('EXISTS', key, callback=callback)

    def sort(self, key, start=None, num=None, by=None, get=None, desc=False,
             alpha=False, store=None, callback=None):
        if ((start is not None and num is None) or
                (num is not None and start is None)):
            raise ValueError("``start`` and ``num`` must both be specified")

        tokens = [key]
        if by is not None:
            tokens.append('BY')
            tokens.append(by)
        if start is not None and num is not None:
            tokens.append('LIMIT')
            tokens.append(start)
            tokens.append(num)
        if get is not None:
            tokens.append('GET')
            tokens.append(get)
        if desc:
            tokens.append('DESC')
        if alpha:
            tokens.append('ALPHA')
        if store is not None:
            tokens.append('STORE')
            tokens.append(store)
        self.execute_command('SORT', *tokens, callback=callback)

    def getbit(self, key, offset, callback=None):
        self.execute_command('GETBIT', key, offset, callback=callback)

    def setbit(self, key, offset, value, callback=None):
        self.execute_command('SETBIT', key, offset, value, callback=callback)

    def bitcount(self, key, start=None, end=None, callback=None):
        args = [a for a in (key, start, end) if a is not None]
        kwargs = {'callback': callback}
        self.execute_command('BITCOUNT', *args, **kwargs)

    def bitop(self, operation, dest, *keys, **kwargs):
        """
        Perform a bitwise operation using ``operation`` between ``keys`` and
        store the result in ``dest``.
        """
        kwargs = {'callback': kwargs.get('callback', None)}
        self.execute_command('BITOP', operation, dest, *keys, **kwargs)

    ### COUNTERS COMMANDS
    def incr(self, key, callback=None):
        self.execute_command('INCR', key, callback=callback)

    def decr(self, key, callback=None):
        self.execute_command('DECR', key, callback=callback)

    def incrby(self, key, amount, callback=None):
        self.execute_command('INCRBY', key, amount, callback=callback)

    def incrbyfloat(self, key, amount=1.0, callback=None):
        self.execute_command('INCRBYFLOAT', key, amount, callback=callback)

    def decrby(self, key, amount, callback=None):
        self.execute_command('DECRBY', key, amount, callback=callback)

    ### LIST COMMANDS
    def blpop(self, keys, timeout=0, callback=None):
        tokens = to_list(keys)
        tokens.append(timeout)
        self.execute_command('BLPOP', *tokens, callback=callback)

    def brpop(self, keys, timeout=0, callback=None):
        tokens = to_list(keys)
        tokens.append(timeout)
        self.execute_command('BRPOP', *tokens, callback=callback)

    def brpoplpush(self, src, dst, timeout=1, callback=None):
        tokens = [src, dst, timeout]
        self.execute_command('BRPOPLPUSH', *tokens, callback=callback)

    def lindex(self, key, index, callback=None):
        self.execute_command('LINDEX', key, index, callback=callback)

    def llen(self, key, callback=None):
        self.execute_command('LLEN', key, callback=callback)

    def lrange(self, key, start, end, callback=None):
        self.execute_command('LRANGE', key, start, end, callback=callback)

    def lrem(self, key, value, num=0, callback=None):
        self.execute_command('LREM', key, num, value, callback=callback)

    def lset(self, key, index, value, callback=None):
        self.execute_command('LSET', key, index, value, callback=callback)

    def ltrim(self, key, start, end, callback=None):
        self.execute_command('LTRIM', key, start, end, callback=callback)

    def lpush(self, key, *values, **kwargs):
        callback = kwargs.get('callback', None)
        self.execute_command('LPUSH', key, *values, callback=callback)

    def lpushx(self, key, value, callback=None):
        self.execute_command('LPUSHX', key, value, callback=callback)

    def linsert(self, key, where, refvalue, value, callback=None):
        self.execute_command('LINSERT', key, where, refvalue, value,
                             callback=callback)

    def rpush(self, key, *values, **kwargs):
        callback = kwargs.get('callback', None)
        self.execute_command('RPUSH', key, *values, callback=callback)

    def rpushx(self, key, value, **kwargs):
        "Push ``value`` onto the tail of the list ``name`` if ``name`` exists"
        callback = kwargs.get('callback', None)
        self.execute_command('RPUSHX', key, value, callback=callback)

    def lpop(self, key, callback=None):
        self.execute_command('LPOP', key, callback=callback)

    def rpop(self, key, callback=None):
        self.execute_command('RPOP', key, callback=callback)

    def rpoplpush(self, src, dst, callback=None):
        self.execute_command('RPOPLPUSH', src, dst, callback=callback)

    ### SET COMMANDS
    def sadd(self, key, *values, **kwargs):
        callback = kwargs.get('callback', None)
        self.execute_command('SADD', key, *values, callback=callback)

    def srem(self, key, *values, **kwargs):
        callback = kwargs.get('callback', None)
        self.execute_command('SREM', key, *values, callback=callback)

    def scard(self, key, callback=None):
        self.execute_command('SCARD', key, callback=callback)

    def spop(self, key, callback=None):
        self.execute_command('SPOP', key, callback=callback)

    def smove(self, src, dst, value, callback=None):
        self.execute_command('SMOVE', src, dst, value, callback=callback)

    def sismember(self, key, value, callback=None):
        self.execute_command('SISMEMBER', key, value, callback=callback)

    def smembers(self, key, callback=None):
        self.execute_command('SMEMBERS', key, callback=callback)

    def srandmember(self, key, number=None, callback=None):
        if number:
            self.execute_command('SRANDMEMBER', key, number, callback=callback)
        else:
            self.execute_command('SRANDMEMBER', key, callback=callback)

    def sinter(self, keys, callback=None):
        self.execute_command('SINTER', *keys, callback=callback)

    def sdiff(self, keys, callback=None):
        self.execute_command('SDIFF', *keys, callback=callback)

    def sunion(self, keys, callback=None):
        self.execute_command('SUNION', *keys, callback=callback)

    def sinterstore(self, keys, dst, callback=None):
        self.execute_command('SINTERSTORE', dst, *keys, callback=callback)

    def sunionstore(self, keys, dst, callback=None):
        self.execute_command('SUNIONSTORE', dst, *keys, callback=callback)

    def sdiffstore(self, keys, dst, callback=None):
        self.execute_command('SDIFFSTORE', dst, *keys, callback=callback)

    ### SORTED SET COMMANDS
    def zadd(self, key, *score_value, **kwargs):
        callback = kwargs.get('callback', None)
        self.execute_command('ZADD', key, *score_value, callback=callback)

    def zcard(self, key, callback=None):
        self.execute_command('ZCARD', key, callback=callback)

    def zincrby(self, key, value, amount, callback=None):
        self.execute_command('ZINCRBY', key, amount, value, callback=callback)

    def zrank(self, key, value, callback=None):
        self.execute_command('ZRANK', key, value, callback=callback)

    def zrevrank(self, key, value, callback=None):
        self.execute_command('ZREVRANK', key, value, callback=callback)

    def zrem(self, key, *values, **kwargs):
        callback = kwargs.get('callback', None)
        self.execute_command('ZREM', key, *values, callback=callback)

    def zcount(self, key, start, end, callback=None):
        self.execute_command('ZCOUNT', key, start, end, callback=callback)

    def zscore(self, key, value, callback=None):
        self.execute_command('ZSCORE', key, value, callback=callback)

    def zrange(self, key, start, num, with_scores=True, callback=None):
        tokens = [key, start, num]
        if with_scores:
            tokens.append('WITHSCORES')
        self.execute_command('ZRANGE', *tokens, callback=callback)

    def zrevrange(self, key, start, num, with_scores, callback=None):
        tokens = [key, start, num]
        if with_scores:
            tokens.append('WITHSCORES')
        self.execute_command('ZREVRANGE', *tokens, callback=callback)

    def zrangebyscore(self, key, start, end, offset=None, limit=None,
                      with_scores=False, callback=None):
        tokens = [key, start, end]
        if offset is not None:
            tokens.append('LIMIT')
            tokens.append(offset)
            tokens.append(limit)
        if with_scores:
            tokens.append('WITHSCORES')
        self.execute_command('ZRANGEBYSCORE', *tokens, callback=callback)

    def zrevrangebyscore(self, key, end, start, offset=None, limit=None,
                         with_scores=False, callback=None):
        tokens = [key, end, start]
        if offset is not None:
            tokens.append('LIMIT')
            tokens.append(offset)
            tokens.append(limit)
        if with_scores:
            tokens.append('WITHSCORES')
        self.execute_command('ZREVRANGEBYSCORE', *tokens, callback=callback)

    def zremrangebyrank(self, key, start, end, callback=None):
        self.execute_command('ZREMRANGEBYRANK', key, start, end,
                             callback=callback)

    def zremrangebyscore(self, key, start, end, callback=None):
        self.execute_command('ZREMRANGEBYSCORE', key, start, end,
                             callback=callback)

    def zinterstore(self, dest, keys, aggregate=None, callback=None):
        return self._zaggregate('ZINTERSTORE', dest, keys, aggregate, callback)

    def zunionstore(self, dest, keys, aggregate=None, callback=None):
        return self._zaggregate('ZUNIONSTORE', dest, keys, aggregate, callback)

    def _zaggregate(self, command, dest, keys, aggregate, callback):
        tokens = [dest, len(keys)]
        if isinstance(keys, dict):
            items = list(keys.items())
            keys = [i[0] for i in items]
            weights = [i[1] for i in items]
        else:
            weights = None
        tokens.extend(keys)
        if weights:
            tokens.append('WEIGHTS')
            tokens.extend(weights)
        if aggregate:
            tokens.append('AGGREGATE')
            tokens.append(aggregate)
        self.execute_command(command, *tokens, callback=callback)

    ### HASH COMMANDS
    def hgetall(self, key, callback=None):
        self.execute_command('HGETALL', key, callback=callback)

    def hmset(self, key, mapping, callback=None):
        items = [i for k, v in list(mapping.items()) for i in (k, v)]
        self.execute_command('HMSET', key, *items, callback=callback)

    def hset(self, key, field, value, callback=None):
        self.execute_command('HSET', key, field, value, callback=callback)

    def hsetnx(self, key, field, value, callback=None):
        self.execute_command('HSETNX', key, field, value, callback=callback)

    def hget(self, key, field, callback=None):
        self.execute_command('HGET', key, field, callback=callback)

    def hdel(self, key, *fields, **kwargs):
        callback = kwargs.get('callback')
        self.execute_command('HDEL', key, *fields, callback=callback)

    def hlen(self, key, callback=None):
        self.execute_command('HLEN', key, callback=callback)

    def hexists(self, key, field, callback=None):
        self.execute_command('HEXISTS', key, field, callback=callback)

    def hincrby(self, key, field, amount=1, callback=None):
        self.execute_command('HINCRBY', key, field, amount, callback=callback)

    def hincrbyfloat(self, key, field, amount=1.0, callback=None):
        self.execute_command('HINCRBYFLOAT', key, field, amount,
                             callback=callback)

    def hkeys(self, key, callback=None):
        self.execute_command('HKEYS', key, callback=callback)

    def hmget(self, key, fields, callback=None):
        self.execute_command('HMGET', key, *fields, callback=callback)

    def hvals(self, key, callback=None):
        self.execute_command('HVALS', key, callback=callback)

    ### SCAN COMMANDS
    def scan(self, cursor, count=None, match=None, callback=None):
        self._scan('SCAN', cursor, count, match, callback)

    def hscan(self, key, cursor, count=None, match=None, callback=None):
        self._scan('HSCAN', cursor, count, match, callback, key=key)

    def sscan(self, key, cursor, count=None, match=None, callback=None):
        self._scan('SSCAN', cursor, count, match, callback, key=key)

    def zscan(self, key, cursor, count=None, match=None, callback=None):
        self._scan('ZSCAN', cursor, count, match, callback, key=key)

    def _scan(self, cmd, cursor, count, match, callback, key=None):
        tokens = [cmd]
        key and tokens.append(key)
        tokens.append(cursor)
        match and tokens.extend(['MATCH', match])
        count and tokens.extend(['COUNT', count])
        self.execute_command(*tokens, callback=callback)

    ### GEO COMMANDS
    def geoadd(self, key, longitude, latitude, member, *args, **kwargs):
        self.execute_command('GEOADD', key, longitude, latitude, member, *args, **kwargs)

    def geodist(self, key, member1, member2, unit='m', callback=None):
        self.execute_command('GEODIST', key, member1, member2, unit, callback=callback)

    def geohash(self, key, member, *args, **kwargs):
        self.execute_command('GEOHASH', key, member, *args, **kwargs)

    def geopos(self, key, member, *args, **kwargs):
        self.execute_command('GEOPOS', key, member, *args, **kwargs)

    def georadius(self, key, longitude, latitude, radius, unit='m',
                  with_coord=False, with_dist=False, with_hash=False,
                  count=None, sort=None, callback=None):
        args = []

        if with_coord:
            args.append('WITHCOORD')
        if with_dist:
            args.append('WITHDIST')
        if with_hash:
            args.append('WITHHASH')

        if count and count > 0:
            args.append(count)
        if sort and sort in ['ASC', 'DESC']:
            args.append(sort)

        self.execute_command('GEORADIUS', key, longitude, latitude, radius, unit, callback=callback, *args)

    def georadiusbymember(self, key, member, radius, unit='m',
                          with_coord=False, with_dist=False, with_hash=False,
                          count=None, sort=None, callback=None):
        args = []

        if with_coord:
            args.append('WITHCOORD')
        if with_dist:
            args.append('WITHDIST')
        if with_hash:
            args.append('WITHHASH')

        if count and count > 0:
            args.append(count)
        if sort and sort in ['ASC', 'DESC']:
            args.append(sort)

        self.execute_command('GEORADIUSBYMEMBER', key, member, radius, unit, callback=callback, *args)

    ### PUBSUB
    def subscribe(self, channels, callback=None):
        self._subscribe('SUBSCRIBE', channels, callback=callback)

    def psubscribe(self, channels, callback=None):
        self._subscribe('PSUBSCRIBE', channels, callback=callback)

    def _subscribe(self, cmd, channels, callback=None):
        if isinstance(channels, str) or (not PY3 and isinstance(channels, str)):
            channels = [channels]
        if not self.subscribed:
            listen_callback = None
            original_cb = stack_context.wrap(callback) if callback else None

            def _cb(*args, **kwargs):
                self.on_subscribed(Message(kind='subscribe',
                                           channel=channels[0],
                                           body=None,
                                           pattern=None))
                if original_cb:
                    original_cb(True)

            callback = _cb
        else:
            listen_callback = callback
            callback = None
        # Use the listen loop to execute subscribe callbacks
        for channel in channels:
            self.subscribe_callbacks.append((channel, listen_callback))
            # Do not execute the same callback multiple times
            listen_callback = None
        self.execute_command(cmd, *channels, callback=callback)

    def on_subscribed(self, result):
        self.subscribed.add(result.channel)

    def on_unsubscribed(self, channels, *args, **kwargs):
        channels = set(channels)
        self.subscribed -= channels
        for cb_channels, cb in self.unsubscribe_callbacks:
            cb_channels.difference_update(channels)
            if not cb_channels:
                self._io_loop.add_callback(cb)

    def unsubscribe(self, channels, callback=None):
        self._unsubscribe('UNSUBSCRIBE', channels, callback=callback)

    def punsubscribe(self, channels, callback=None):
        self._unsubscribe('PUNSUBSCRIBE', channels, callback=callback)

    def _unsubscribe(self, cmd, channels, callback=None):
        if isinstance(channels, str) or (not PY3 and isinstance(channels, str)):
            channels = [channels]
        if callback:
            cb = stack_context.wrap(callback)
            # TODO: Do we need to back this up with self._io_loop.add_timeout(time() + 1, cb)?
            # FIXME: What about PUNSUBSCRIBEs?
            self.unsubscribe_callbacks.append((set(channels), cb))
        self.execute_command(cmd, *channels)

    def publish(self, channel, message, callback=None):
        self.execute_command('PUBLISH', channel, message, callback=callback)

    @gen.engine
    def listen(self, callback=None, exit_callback=None):
        """
        Starts a Pub/Sub channel listening loop.
        Use the unsubscribe or punsubscribe methods to exit it.

        Each received message triggers the callback function.

        Callback function receives a Message object instance as argument.

        Here is an example of handling a channel subscription::

            def handle_message(msg):
                if msg.kind == 'message':
                    print msg.body
                elif msg.kind == 'disconnect':
                    # Disconnected from the redis server
                    pass

            yield gen.Task(client.subscribe, 'channel_name')
            client.listen(handle_message)
            ...
            yield gen.Task(client.subscribe, 'another_channel_name')
            ...
            yield gen.Task(client.unsubscribe, 'another_channel_name')
            yield gen.Task(client.unsubscribe, 'channel_name')

        Unsubscribe from a channel to exit the 'listen' loop.
        """
        if callback:
            def error_wrapper(e):
                if isinstance(e, GeneratorExit):
                    return ConnectionError('Connection lost')
                else:
                    return e

            cmd_listen = CmdLine('LISTEN')
            while self.subscribed:
                try:
                    data = yield gen.Task(self.connection.readline)
                except Exception as e:
                    # Maybe wrong!
                    import logging
                    logging.exception(e)

                    data = None

                if data is None:
                    # If disconnected from the redis server clear the list
                    # of subscriber this client has subscribed to
                    channels = self.subscribed
                    self.subscribed = set()
                    # send a message to caller:
                    # Message(kind='disconnect', channel=set(channel1, ...))
                    callback(reply_pubsub_message(('disconnect', channels)))
                    return

                response = self.process_data(data, cmd_listen)

                if isinstance(response, partial):
                    response = yield gen.Task(response)
                if isinstance(response, Exception):
                    raise response

                result = self.format_reply(cmd_listen, response)

                if result and result.kind in ('subscribe', 'psubscribe'):
                    self.on_subscribed(result)
                    try:
                        __, cb = self.subscribe_callbacks.popleft()
                    except IndexError:
                        __, cb = result.channel, None
                    if cb:
                        cb(True)

                if result and result.kind in ('unsubscribe', 'punsubscribe'):
                    self.on_unsubscribed([result.channel])

                callback(result)

        if exit_callback:
            exit_callback(bool(callback))

    ### CAS
    def watch(self, *key_names, **kwargs):
        callback = kwargs.get('callback', None)
        self.execute_command('WATCH', *key_names, callback=callback)

    def unwatch(self, callback=None):
        self.execute_command('UNWATCH', callback=callback)

    ### LOCKS
    def lock(self, lock_name, lock_ttl=None, polling_interval=0.1):
        """
        Create a new Lock object using the Redis key ``lock_name`` for
        state, that behaves like a threading.Lock.

        This method is synchronous, and returns immediately with the Lock object.
        This method doesn't acquire the Lock or in fact trigger any sort of
        communications with the Redis server. This must be done using the Lock
        object itself.

        If specified, ``lock_ttl`` indicates the maximum life time for the lock.
        If none is specified, it will remain locked until release() is called.

        ``polling_interval`` indicates the time between acquire attempts (polling)
        when the lock is in blocking mode and another client is currently
        holding the lock.

        Note: If using ``lock_ttl``, you should make sure all the hosts
        that are running clients have their time synchronized with a network
        time service like ntp.
        """
        return Lock(self, lock_name, lock_ttl=lock_ttl, polling_interval=polling_interval)

    ### SCRIPTING COMMANDS
    def eval(self, script, keys=None, args=None, callback=None):
        if keys is None:
            keys = []
        if args is None:
            args = []
        num_keys = len(keys)
        _args = keys + args
        self.execute_command('EVAL', script, num_keys,
                             *_args, callback=callback)

    def evalsha(self, shahash, keys=None, args=None, callback=None):
        if keys is None:
            keys = []
        if args is None:
            args = []
        num_keys = len(keys)
        keys.extend(args)
        self.execute_command('EVALSHA', shahash, num_keys,
                             *keys, callback=callback)

    def script_exists(self, shahashes, callback=None):
        # not yet implemented in the redis protocol
        self.execute_command('SCRIPT EXISTS', *shahashes, callback=callback)

    def script_flush(self, callback=None):
        # not yet implemented in the redis protocol
        self.execute_command('SCRIPT FLUSH', callback=callback, verbose=True)

    def script_kill(self, callback=None):
        # not yet implemented in the redis protocol
        self.execute_command('SCRIPT KILL', callback=callback)

    def script_load(self, script, callback=None):
        # not yet implemented in the redis protocol
        self.execute_command('SCRIPT LOAD', script, callback=callback)


class Pipeline(Client):
    def __init__(self, transactional, *args, **kwargs):
        super(Pipeline, self).__init__(*args, **kwargs)
        self.transactional = transactional
        self.command_stack = []
        self.executing = False

    def __del__(self):
        """
        Do not disconnect on releasing the PipeLine object.
        Thanks to Tomek (https://github.com/thlawiczka)
        """
        pass

    def execute_command(self, cmd, *args, **kwargs):
        if self.executing and cmd in ('AUTH', 'SELECT'):
            super(Pipeline, self).execute_command(cmd, *args, **kwargs)
        elif cmd in PUB_SUB_COMMANDS:
            raise RequestError(
                'Client is not supposed to issue '
                'the %s command in a pipeline' % cmd)
        else:
            self.command_stack.append(CmdLine(cmd, *args, **kwargs))

    def discard(self):
        # actually do nothing with redis-server, just flush the command_stack
        self.command_stack = []

    def format_replies(self, cmd_lines, responses):
        results = []
        for cmd_line, response in zip(cmd_lines, responses):
            try:
                results.append(self.format_reply(cmd_line, response))
            except Exception as e:
                results.append(e)
        return results

    def format_pipeline_request(self, command_stack):
        return ''.join(self.format_command(c.cmd, *c.args, **c.kwargs)
                       for c in command_stack)

    @gen.engine
    def execute(self, callback=None):
        command_stack = self.command_stack
        self.command_stack = []
        self.executing = True
        try:
            if self.transactional:
                command_stack = ([CmdLine('MULTI')] +
                                 command_stack +
                                 [CmdLine('EXEC')])

            request = self.format_pipeline_request(command_stack)

            password_should_be_sent = (
                self.password and
                self.connection.info.get('pass', None) != self.password)
            if password_should_be_sent:
                yield gen.Task(self.auth, self.password)
            db_should_be_selected = (
                self.selected_db and
                self.connection.info.get('db', None) != self.selected_db)
            if db_should_be_selected:
                yield gen.Task(self.select, self.selected_db)

            if not self.connection.connected():
                self.connection.connect()

            if not self.connection.ready():
                yield gen.Task(self.connection.wait_until_ready)

            try:
                self.connection.write(request)
            except IOError:
                self.command_stack = []
                self.connection.disconnect()
                raise ConnectionError("Socket closed on remote end")
            except Exception as e:
                self.command_stack = []
                self.connection.disconnect()
                raise e

            responses = []
            total = len(command_stack)
            cmds = iter(command_stack)

            while len(responses) < total:
                data = yield gen.Task(self.connection.readline)
                if not data:
                    raise ResponseError('Not enough data after EXEC')
                try:
                    cmd_line = next(cmds)
                    if self.transactional and cmd_line.cmd != 'EXEC':
                        response = self.process_data(data,
                                                     CmdLine('MULTI_PART'))
                    else:
                        response = self.process_data(data, cmd_line)
                    if isinstance(response, partial):
                        response = yield gen.Task(response)
                    responses.append(response)
                except Exception as e:
                    responses.append(e)

            if self.transactional:
                command_stack = command_stack[:-1]
                responses = responses[-1]
                results = self.format_replies(command_stack[1:], responses)
            else:
                results = self.format_replies(command_stack, responses)

            self.connection.execute_pending_command()
        finally:
            self.executing = False

        callback(results)


class Lock(object):
    """
    A shared, distributed Lock that uses a Redis server to hold its state.
    This Lock can be shared across processes and/or machines. It works
    asynchronously and plays nice with the Tornado IOLoop.
    """

    LOCK_FOREVER = float(2 ** 31 + 1)  # 1 past max unix time

    def __init__(self, redis_client, lock_name, lock_ttl=None, polling_interval=0.1):
        """
        Create a new Lock object using the Redis key ``lock_name`` for
        state, that behaves like a threading.Lock.

        This method is synchronous, and returns immediately. It doesn't acquire the
        Lock or in fact trigger any sort of communications with the Redis server.
        This must be done using the Lock object itself.

        If specified, ``lock_ttl`` indicates the maximum life time for the lock.
        If none is specified, it will remain locked until release() is called.

        ``polling_interval`` indicates the time between acquire attempts (polling)
        when the lock is in blocking mode and another client is currently
        holding the lock.

        Note: If using ``lock_ttl``, you should make sure all the hosts
        that are running clients have their time synchronized with a network
        time service like ntp.
        """
        self.redis_client = redis_client
        self.lock_name = lock_name
        self.acquired_until = None
        self.lock_ttl = lock_ttl
        self.polling_interval = polling_interval
        if self.lock_ttl and self.polling_interval > self.lock_ttl:
            raise LockError("'polling_interval' must be less than 'lock_ttl'")

    @gen.engine
    def acquire(self, blocking=True, callback=None):
        """
        Acquire the lock.
        Returns True once the lock is acquired.

        If ``blocking`` is False, always return immediately. If the lock
        was acquired, return True, otherwise return False.
        Otherwise, block until the lock is acquired (or an error occurs).

        If ``callback`` is supplied, it is called with the result.
        """

        # Loop until we have a conclusive result
        while 1:

            # Get the current time
            unixtime = int(mod_time.time())

            # If the lock has a limited lifetime, create a timeout value
            if self.lock_ttl:
                timeout_at = unixtime + self.lock_ttl
            # Otherwise, set the timeout value at forever (dangerous)
            else:
                timeout_at = Lock.LOCK_FOREVER
            timeout_at = float(timeout_at)

            # Try and get the lock, setting the timeout value in the appropriate key,
            # but only if a previous value does not exist in Redis
            result = yield gen.Task(self.redis_client.setnx, self.lock_name, timeout_at)

            # If we managed to get the lock
            if result:

                # We successfully acquired the lock!
                self.acquired_until = timeout_at
                if callback:
                    callback(True)
                return

            # We didn't get the lock, another value is already there
            # Check to see if the current lock timeout value has already expired
            result = yield gen.Task(self.redis_client.get, self.lock_name)
            existing = float(result or 1)

            # Has it expired?
            if existing < unixtime:

                # The previous lock is expired. We attempt to overwrite it, getting the current value
                # in the server, just in case someone tried to get the lock at the same time
                result = yield gen.Task(self.redis_client.getset,
                                        self.lock_name,
                                        timeout_at)
                existing = float(result or 1)

                # If the value we read is older than our own current timestamp, we managed to get the
                # lock with no issues - the timeout has indeed expired
                if existing < unixtime:

                    # We successfully acquired the lock!
                    self.acquired_until = timeout_at
                    if callback:
                        callback(True)
                    return

                    # However, if we got here, then the value read from the Redis server is newer than
                    # our own current timestamp - meaning someone already got the lock before us.
                    # We failed getting the lock.

            # If we are not signalled to block
            if not blocking:

                # We failed acquiring the lock...
                if callback:
                    callback(False)
                return

            # Otherwise, we "sleep" for an amount of time equal to the polling interval, after which
            # we will try getting the lock again.
            yield gen.Task(self.redis_client._io_loop.add_timeout,
                           self.redis_client._io_loop.time() + self.polling_interval)

    @gen.engine
    def release(self, callback=None):
        """
        Releases the already acquired lock.

        If ``callback`` is supplied, it is called with True when finished.
        """

        if self.acquired_until is None:
            raise ValueError("Cannot release an unlocked lock")

        # Get the current lock value
        result = yield gen.Task(self.redis_client.get, self.lock_name)
        existing = float(result or 1)

        # If the lock time is in the future, delete the lock
        if existing >= self.acquired_until:
            yield gen.Task(self.redis_client.delete, self.lock_name)
        self.acquired_until = None

        # That is it.
        if callback:
            callback(True)
