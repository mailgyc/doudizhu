import sys
import time

from tornado.testing import AsyncTestCase

import tornadoredis


def get_callable(obj):
    return hasattr(obj, '__call__')


def async_test_ex(timeout=5):
    def _inner(func):
        def _runner(self, *args, **kwargs):
            try:
                func(self, *args, **kwargs)
            except:
                self.stop()
                raise
            return self.wait(timeout=timeout)
        return _runner
    return _inner


def async_test(func):
    _inner = async_test_ex()
    return _inner(func)


class TestRedisClient(tornadoredis.Client):

    def __init__(self, *args, **kwargs):
        self._on_destroy = kwargs.get('on_destroy', None)
        if 'on_destroy' in kwargs:
            del kwargs['on_destroy']
        super(TestRedisClient, self).__init__(*args, **kwargs)

    def __del__(self):
        super(TestRedisClient, self).__del__()
        if self._on_destroy:
            self._on_destroy()


if sys.version_info < (2, 7):
    _MAX_LENGTH = 80
    def safe_repr(obj, short=False):
        try:
            result = repr(obj)
        except Exception:
            result = object.__repr__(obj)
        if not short or len(result) < _MAX_LENGTH:
            return result
        return result[:_MAX_LENGTH] + ' [truncated]...'


class RedisTestCase(AsyncTestCase):
    test_db = 9
    test_port = 6379

    if sys.version_info < (2, 7):
        def assertIn(self, test_value, expected_set):
            msg = "%s did not occur in %s" % (test_value, expected_set)
            self.assertTrue(test_value in expected_set, msg)

        def assertIsInstance(self, obj, cls, msg=None):
            """Same as self.assertTrue(isinstance(obj, cls)), with a nicer
            default message."""
            if not isinstance(obj, cls):
                standardMsg = '%s is not an instance of %r' % (safe_repr(obj), cls)
                self.fail(self._formatMessage(msg, standardMsg))

        def assertGreater(self, a, b, msg=None):
            """Just like self.assertTrue(a > b), but with a nicer default message."""
            if not a > b:
                standardMsg = '%s not greater than %s' % (safe_repr(a), safe_repr(b))
                self.fail(self._formatMessage(msg, standardMsg))

        def assertGreaterEqual(self, a, b, msg=None):
            if not a >= b:
                standardMsg = '%s not greater than or equal to %s' % (safe_repr(a), safe_repr(b))
                self.fail(self._formatMessage(msg, standardMsg))

        def assertLessEqual(self, a, b, msg=None):
            if not a <= b:
                standardMsg = '%s not less than or equal to %s' % (safe_repr(a), safe_repr(b))
                self.fail(self._formatMessage(msg, standardMsg))

    def setUp(self, flush=True):
        super(RedisTestCase, self).setUp()
        self.client = self._new_client()
        if flush:
            self.client.flushdb()

    def tearDown(self):
        try:
            self.client.connection.disconnect()
            del self.client
        except AttributeError:
            pass
        super(RedisTestCase, self).tearDown()

    def _new_client(self, pool=None, on_destroy=None, selected_db=None):
        if selected_db is None:
            selected_db = self.test_db
        client = TestRedisClient(io_loop=self.io_loop,
                                 port=self.test_port,
                                 selected_db=selected_db,
                                 connection_pool=pool,
                                 on_destroy=on_destroy)
        return client

    def delayed(self, timeout, cb):
        self.io_loop.add_timeout(time.time() + timeout, cb)

    def pause(self, timeout=0.1, callback=None):
        self.io_loop.add_timeout(time.time() + timeout, callback)
