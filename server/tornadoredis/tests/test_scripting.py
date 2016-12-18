import copy
import hashlib
from tornado import gen

from .redistest import RedisTestCase, async_test


class ScriptingTestCase(RedisTestCase):

    @async_test
    @gen.engine
    def test_eval(self):
        script = 'return 2'
        script_digest = hashlib.sha1(script.encode('utf-8')).hexdigest()

        results = yield gen.Task(self.client.eval, script)
        self.assertEqual(2, results)

        # test evalsha
        results = yield gen.Task(self.client.evalsha, script_digest)
        self.assertEqual(2, results)

        self.stop()

    # TODO: script_exists, script_load, script_flush, script_kill
    @async_test
    @gen.engine
    def test_eval_with_args(self):
        key, value = 'test:key:eval', 'value:eval'
        # make sure that key does not exists
        yield gen.Task(self.client.delete, key)

        script = """
        if redis.call('SETNX', KEYS[1], ARGV[1])==1
        then
            return 'foo'
        else
            return 'bar'
        end
        """
        keys = [key]
        _keys_copy = copy.deepcopy(keys)
        args = [value]

        results = yield gen.Task(self.client.eval, script, keys, args)
        self.assertEqual('foo', results)
        # compare keys after eval command and initial keys (_keys_copy)
        # to make sure that *eval* command does not change keys list
        self.assertEqual(keys, _keys_copy)
        results = yield gen.Task(self.client.eval, script, keys, args)
        self.assertEqual('bar', results)
        self.assertEqual(keys, _keys_copy)

        self.stop()
