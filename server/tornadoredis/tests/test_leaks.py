import sys
import gc
import random

from tornado import gen
import tornado.ioloop

from tornadoredis.exceptions import ResponseError

from .redistest import RedisTestCase, async_test


try:
    PYPY_INTERPRETER = 'PyPy' in sys.version
except AttributeError:
    PYPY_INTERPRETER = False


class MiscTestCase(RedisTestCase):
    @async_test
    @gen.engine
    def test_response_error(self):
        res = yield gen.Task(self.client.set, 'foo', 'bar')
        self.assertTrue(res)
        res = yield gen.Task(self.client.llen, 'foo')
        self.assertIsInstance(res, ResponseError)
        self.stop()

    @async_test
    @gen.engine
    def test_for_memory_leaks(self):
        """
        Tests if a Client instance destroyed properly
        """
        def some_code(callback=None):
            c = self._new_client(on_destroy=callback)
            c.get('foo')
            # Force pypy to do the garbage collection
            if PYPY_INTERPRETER:
                del c
                gc.collect()

        for __ in range(1, 3):
            yield gen.Task(some_code)

        self.stop()

    @async_test
    @gen.engine
    def test_for_memory_leaks_gen(self):
        @gen.engine
        def some_code(on_destroy=None, callback=None):
            c = self._new_client(on_destroy=on_destroy)
            n = '%d' % random.randint(1, 1000)
            yield gen.Task(c.set, 'foo', n)
            n2 = yield gen.Task(c.get, 'foo')
            self.assertEqual(n, n2)
            tornado.ioloop.IOLoop.current().add_callback(callback)

        yield gen.Task(some_code, on_destroy=(yield gen.Callback('destroy')))
        gc.collect()
        yield gen.Wait('destroy')

        self.stop()

    if sys.version_info >= (2, 7):
        @async_test
        @gen.engine
        def test_with(self):
            """
            Find a way to destroy client instances created by
            tornado.gen-wrapped functions.
            """
            @gen.engine
            def some_code(callback=None):
                with self._new_client(on_destroy=callback) as c:
                    n = '%d' % random.randint(1, 1000)
                    yield gen.Task(c.set, 'foo', n)
                    n2 = yield gen.Task(c.get, 'foo')
                    self.assertEqual(n, n2)
                # Force pypy to do the garbage collection
                if PYPY_INTERPRETER:
                    del c
                    gc.collect()

            yield gen.Task(some_code)

            self.stop()

    @async_test
    @gen.engine
    def test_for(self):
        """
        Find a way to destroy client instances created by
        tornado.gen-wrapped functions.
        """
        @gen.engine
        def some_code(callback=None):
            c = self._new_client(on_destroy=callback)
            for n in range(1, 5):
                yield gen.Task(c.set, 'foo', n)
                n2 = yield gen.Task(c.get, 'foo')
                self.assertEqual('%d' % n, n2)
            # Force pypy to do the garbage collection
            if PYPY_INTERPRETER:
                del c
                gc.collect()

        yield gen.Task(some_code)

        self.stop()
