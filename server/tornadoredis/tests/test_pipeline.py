from tornado import gen

from .redistest import RedisTestCase, async_test
from tornadoredis.exceptions import ResponseError


class PipelineTestCase(RedisTestCase):

    @async_test
    @gen.engine
    def test_pipe_simple(self):
        pipe = self.client.pipeline()
        pipe.set('foo', '123')
        pipe.set('bar', '456')
        pipe.mget(('foo', 'bar'))

        res = yield gen.Task(pipe.execute)
        self.assertEqual(res, [True, True, ['123', '456', ]])
        self.stop()

    @async_test
    @gen.engine
    def test_pipe_multi(self):
        pipe = self.client.pipeline(transactional=True)
        pipe.set('foo', '123')
        pipe.set('bar', '456')
        pipe.mget(('foo', 'bar'))

        res = yield gen.Task(pipe.execute)
        self.assertEqual(res, [True, True, ['123', '456', ]])
        self.stop()

    @async_test
    @gen.engine
    def test_pipe_error(self):
        pipe = self.client.pipeline()
        pipe.sadd('foo', 1)
        pipe.sadd('foo', 2)
        pipe.rpop('foo')

        res = yield gen.Task(pipe.execute)
        self.assertEqual(res[:2], [1, 1])
        self.assertIsInstance(res[2], ResponseError)
        self.stop()

    @async_test
    @gen.engine
    def test_two_pipes(self):
        pipe = self.client.pipeline()

        pipe.rpush('foo', '1')
        pipe.rpush('foo', '2')
        pipe.lrange('foo', 0, -1)
        res = yield gen.Task(pipe.execute)
        self.assertEqual(res, [True, 2, ['1', '2']])

        pipe.sadd('bar', '3')
        pipe.sadd('bar', '4')
        pipe.smembers('bar')
        pipe.scard('bar')
        res = yield gen.Task(pipe.execute)
        self.assertEqual(res, [1, 1, set(['3', '4']), 2])

        self.stop()

    @async_test
    @gen.engine
    def test_mix_with_pipe(self):
        pipe = self.client.pipeline()

        res = yield gen.Task(self.client.set, 'foo', '123')
        self.assertTrue(res)
        yield gen.Task(self.client.hmset, 'bar', {'zar': 'gza'},)

        pipe.get('foo')
        res = yield gen.Task(self.client.get, 'foo')
        self.assertEqual(res, '123')

        pipe.hgetall('bar')

        res = yield gen.Task(pipe.execute)
        self.assertEqual(res, ['123', {'zar': 'gza'}])
        self.stop()

    @async_test
    @gen.engine
    def test_mix_with_pipe_multi(self):
        pipe = self.client.pipeline(transactional=True)

        res = yield gen.Task(self.client.set, 'foo', '123')
        self.assertTrue(res)
        yield gen.Task(self.client.hmset, 'bar', {'zar': 'gza'},)

        pipe.get('foo')
        res = yield gen.Task(self.client.get, 'foo')
        self.assertEqual(res, '123')

        pipe.hgetall('bar')

        res = yield gen.Task(pipe.execute)
        self.assertEqual(res, ['123', {'zar': 'gza'}])

        self.stop()

    @async_test
    @gen.engine
    def test_pipe_watch(self):
        res = yield gen.Task(self.client.watch, 'foo')
        self.assertTrue(res)
        res = yield gen.Task(self.client.set, 'bar', 'zar')
        self.assertTrue(res)
        pipe = self.client.pipeline(transactional=True)
        pipe.get('bar')
        res = yield gen.Task(pipe.execute)
        self.assertEqual(res, ['zar', ])

        self.stop()

    @async_test
    @gen.engine
    def test_pipe_watch2(self):
        res = yield gen.Task(self.client.set, 'foo', 'bar')
        self.assertTrue(res)
        res = yield gen.Task(self.client.watch, 'foo')
        self.assertTrue(res)
        res = yield gen.Task(self.client.set, 'foo', 'zar')
        self.assertTrue(res)
        pipe = self.client.pipeline(transactional=True)
        pipe.get('foo')
        res = yield gen.Task(pipe.execute)
        self.assertEqual(res, [])

        self.stop()

    @async_test
    @gen.engine
    def test_pipe_watch3(self):
        res = yield gen.Task(self.client.set, 'foo', 'bar')
        self.assertTrue(res)
        res = yield gen.Task(self.client.watch, 'foo1', 'foo2', 'foo')
        self.assertTrue(res)
        res = yield gen.Task(self.client.set, 'foo', 'zar')
        self.assertTrue(res)
        pipe = self.client.pipeline(transactional=True)
        pipe.get('foo')
        res = yield gen.Task(pipe.execute)

        self.stop()

    @async_test
    @gen.engine
    def test_pipe_unwatch(self):
        res = yield gen.Task(self.client.set, 'foo', 'bar')
        self.assertTrue(res)
        res = yield gen.Task(self.client.watch, 'foo')
        self.assertTrue(res)
        res = yield gen.Task(self.client.set, 'foo', 'zar')
        self.assertTrue(res)
        res = yield gen.Task(self.client.unwatch)
        self.assertTrue(res)
        pipe = self.client.pipeline(transactional=True)
        pipe.get('foo')
        res = yield gen.Task(pipe.execute)
        self.assertEqual(res, ['zar'])

        self.stop()

    @async_test
    @gen.engine
    def test_pipe_zsets(self):
        pipe = self.client.pipeline(transactional=True)

        pipe.zadd('foo', 1, 'a')
        pipe.zadd('foo', 2, 'b')
        pipe.zscore('foo', 'a')
        pipe.zscore('foo', 'b')
        pipe.zrank('foo', 'a',)
        pipe.zrank('foo', 'b',)

        pipe.zrange('foo', 0, -1, True)
        pipe.zrange('foo', 0, -1, False)

        res = yield gen.Task(pipe.execute)
        self.assertEqual(res, [
            1, 1,
            1, 2,
            0, 1,
            [('a', 1.0), ('b', 2.0)],
            ['a', 'b'],
        ])
        self.stop()

    @async_test
    @gen.engine
    def test_pipe_zsets2(self):
        pipe = self.client.pipeline(transactional=False)

        pipe.zadd('foo', 1, 'a')
        pipe.zadd('foo', 2, 'b')
        pipe.zscore('foo', 'a')
        pipe.zscore('foo', 'b')
        pipe.zrank('foo', 'a',)
        pipe.zrank('foo', 'b',)

        pipe.zrange('foo', 0, -1, True)
        pipe.zrange('foo', 0, -1, False)

        res = yield gen.Task(pipe.execute)
        self.assertEqual(res, [
            1, 1,
            1, 2,
            0, 1,
            [('a', 1.0), ('b', 2.0)],
            ['a', 'b'],
        ])
        self.stop()

    @async_test
    @gen.engine
    def test_pipe_hsets(self):
        pipe = self.client.pipeline(transactional=True)
        pipe.hset('foo', 'bar', 'aaa')
        pipe.hset('foo', 'zar', 'bbb')
        pipe.hgetall('foo')

        res = yield gen.Task(pipe.execute)
        self.assertEqual(res, [
            True,
            True,
            {'bar': 'aaa', 'zar': 'bbb'}
        ])
        self.stop()

    @async_test
    @gen.engine
    def test_pipe_hsets2(self):
        pipe = self.client.pipeline(transactional=False)
        pipe.hset('foo', 'bar', 'aaa')
        pipe.hset('foo', 'zar', 'bbb')
        pipe.hgetall('foo')

        res = yield gen.Task(pipe.execute)
        self.assertEqual(res, [
            True,
            True,
            {'bar': 'aaa', 'zar': 'bbb'}
        ])
        self.stop()

    @async_test
    @gen.engine
    def test_with(self):
        with self.client.pipeline() as pipe:
            pipe.set('foo', '123')
            pipe.set('bar', '456')
            pipe.mget(('foo', 'bar'))

            res = yield gen.Task(pipe.execute)
        self.assertEqual(res, [True, True, ['123', '456', ]])
        self.stop()
