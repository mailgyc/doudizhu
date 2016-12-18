import sys
import socket
from functools import partial
import weakref
from collections import deque

from tornado.iostream import IOStream
from tornado import stack_context

from .exceptions import ConnectionError

CRLF = b'\r\n'


class Connection(object):
    def __init__(self, host='localhost', port=6379, unix_socket_path=None,
                 event_handler_proxy=None, stop_after=None, io_loop=None):
        self.host = host
        self.port = port
        self.unix_socket_path = unix_socket_path
        self._event_handler = event_handler_proxy
        self.timeout = stop_after
        self._stream = None
        self._io_loop = io_loop

        self.in_progress = False
        self.read_callbacks = set()
        self.ready_callbacks = deque()
        self._lock = 0
        self.info = {'db': 0, 'pass': None}

    def __del__(self):
        self.disconnect()

    def execute_pending_command(self):
        # Continue with the pending command execution
        # if all read operations are completed.
        if not self.read_callbacks and self.ready_callbacks:
            # Pop a SINGLE callback from the queue and execute it.
            # The next one will be executed from the code
            # invoked by the callback
            callback = self.ready_callbacks.popleft()
            callback()

    def ready(self):
        return (not self.read_callbacks and
                not self.ready_callbacks)

    def wait_until_ready(self, callback=None):
        if callback:
            if not self.ready():
                callback = stack_context.wrap(callback)
                self.ready_callbacks.append(callback)
            else:
                callback()

    def connect(self):
        if not self._stream:
            try:
                if self.unix_socket_path:
                    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    sock.settimeout(self.timeout)
                    sock.connect(self.unix_socket_path)
                else:
                    sock = socket.create_connection(
                        (self.host, self.port),
                        timeout=self.timeout
                    )
                    sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
                self._stream = IOStream(sock, io_loop=self._io_loop)
                self._stream.set_close_callback(self.on_stream_close)
                self.info['db'] = 0
                self.info['pass'] = None
            except socket.error as e:
                raise ConnectionError(str(e))
            self.fire_event('on_connect')

    def on_stream_close(self):
        if self._stream:
            self.disconnect()
            callbacks = self.read_callbacks
            self.read_callbacks = set()
            for callback in callbacks:
                callback()

    def disconnect(self):
        if self._stream:
            s = self._stream
            self._stream = None
            try:
                if s.socket:
                    s.socket.shutdown(socket.SHUT_RDWR)
                s.close()
            except:
                pass

    def fire_event(self, event):
        event_handler = self._event_handler
        if event_handler:
            try:
                getattr(event_handler, event)()
            except AttributeError:
                pass

    def write(self, data, callback=None):
        if not self._stream:
            raise ConnectionError('Tried to write to '
                                  'non-existent connection')

        if callback:
            callback = stack_context.wrap(callback)
            _callback = lambda: callback(None)
            self.read_callbacks.add(_callback)
            cb = partial(self.read_callback, _callback)
        else:
            cb = None
        try:
            data = bytes(data, encoding='utf-8')
            self._stream.write(data, callback=cb)
        except IOError as e:
            self.disconnect()
            raise ConnectionError(e.message)

    def read(self, length, callback=None):
        try:
            if not self._stream:
                self.disconnect()
                raise ConnectionError('Tried to read from '
                                      'non-existent connection')
            callback = stack_context.wrap(callback)
            self.read_callbacks.add(callback)
            self._stream.read_bytes(length,
                                    callback=partial(self.read_callback,
                                                     callback))
        except IOError:
            self.fire_event('on_disconnect')

    def read_callback(self, callback, *args, **kwargs):
        try:
            self.read_callbacks.remove(callback)
        except KeyError:
            pass
        callback(*args, **kwargs)

    def readline(self, callback=None):
        try:
            if not self._stream:
                self.disconnect()
                raise ConnectionError('Tried to read from non-existent connection')
            callback = stack_context.wrap(callback)
            self.read_callbacks.add(callback)
            callback = partial(self.read_callback, callback)
            self._stream.read_until(CRLF, callback=callback)
        except IOError:
            self.fire_event('on_disconnect')

    def connected(self):
        if self._stream:
            return True
        return False


class ConnectionPool(object):
    """
    'A Redis server connection pool.

    Arguments:
        max_connections - a maximum number of simultaneous
                          connections to a Redis Server,
        wait_for_available - do not raise an exceptionbut wait for a next
                             available connection if a connection limit
                             has been reached.
        **connection_kwargs
    """
    def __init__(self, max_connections=None, wait_for_available=False,
                 **connection_kwargs):
        self.connection_kwargs = connection_kwargs
        self.max_connections = max_connections or 2048
        self.wait_for_available = wait_for_available
        self._created_connections = 0
        self._available_connections = set()
        self._in_use_connections = set()
        self._waiting_clients = set()

    def get_connection(self, event_handler_ref=None):
        """
        Returns a pooled Redis server connection
        """
        try:
            connection = self._available_connections.pop()
        except KeyError:
            connection = self.make_connection()
        if connection:
            connection._event_handler = event_handler_ref
            self._in_use_connections.add(connection)
        elif self.wait_for_available:
            connection = self.make_proxy(client_proxy=event_handler_ref)
        else:
            raise ConnectionError("Too many connections")
        return connection

    def make_proxy(self, client_proxy=None, connected=True):
        """
        Creates a proxy object to substitute client's connection
        until a connection be available
        """
        connection = ConnectionProxy(pool=self,
                                     client_proxy=client_proxy,
                                     connected=connected)
        if connected:
            self._waiting_clients.add(connection)
        return connection

    def make_connection(self):
        """
        Creates a new connection to Redis server
        """
        if self._created_connections >= self.max_connections:
            return None
        self._created_connections += 1
        return Connection(**self.connection_kwargs)

    def release(self, connection):
        """
        Releases the connection back to the pool
        """
        if isinstance(connection, ConnectionProxy):
            try:
                self._waiting_clients.remove(connection)
            except KeyError:
                pass
            return
        connection._event_handler = None
        if self._waiting_clients:
            waiting = self._waiting_clients.pop()
            waiting.assign_connection(connection)
        else:
            try:
                self._in_use_connections.remove(connection)
            except (KeyError, ValueError):
                pass
            self._available_connections.add(connection)

    def reconnect(self, connection_proxy):
        if self._available_connections:
            connection = self._available_connections.pop()
            connection_proxy.assign_connection(connection)
        else:
            self._waiting_clients.add(connection_proxy)


class ConnectionProxy(object):
    """
    A stub object to replace a client's connection until one is available.
    """
    def __init__(self, pool=None, client_proxy=None, connected=True):
        self.client = client_proxy
        self._pool = weakref.ref(pool)
        self.ready_callbacks = []
        self._connected = connected
        self.info = {'db': -1}

    @property
    def pool(self):
        return self._pool()

    def connected(self):
        return self._connected

    def connect(self):
        # Add this proxy to the waiting_clients list
        if not self._connected:
            self.pool.reconnect(self)
            self._connected = True

    def ready(self):
        return False

    def wait_until_ready(self, callback=None):
        if callback:
            self.ready_callbacks.append(callback)
        return self

    def execute_pending_command(self):
        pass

    def assign_connection(self, connection):
        """
        Replaces given connection proxy with the connection object.
        """
        if self.ready_callbacks:
            connection.ready_callbacks += self.ready_callbacks
            self.ready_callbacks = []
        connection._event_handler = self.client
        self.client.connection = connection
        self.pool.release(self)
        if connection.connected():
            connection.fire_event('on_connect')
        connection.execute_pending_command()
