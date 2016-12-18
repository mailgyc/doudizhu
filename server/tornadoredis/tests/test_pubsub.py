# coding=utf-8
from collections import namedtuple
import json
from random import randint
from tornado import gen

from .redistest import RedisTestCase, async_test
from tornadoredis.pubsub import SockJSSubscriber, SocketIOSubscriber


class PubSubTestCase(RedisTestCase):

    def setUp(self):
        super(PubSubTestCase, self).setUp(flush=False)
        self._message_count = 0
        self.publisher = self._new_client()

    def tearDown(self):
        try:
            self.publisher.connection.disconnect()
            del self.publisher
        except AttributeError:
            pass
        super(PubSubTestCase, self).tearDown()

    def pause(self, timeout, callback=None):
        self.delayed(timeout, callback)

    def _expect_messages(self, messages, subscribe_callback=None):
        self._expected_messages = messages
        self._subscribe_callback = subscribe_callback

    def _handle_message(self, msg):
        self._message_count += 1
        self.assertIn(msg.kind, self._expected_messages)
        expected = self._expected_messages[msg.kind]
        self.assertIn(msg.pattern, expected[0::2])
        if 'subscribe' not in msg.kind:
            self.assertIn(msg.body, expected[1::2])
        if msg.kind in ('subscribe', 'psubscribe'):
            if self._subscribe_callback:
                cb = self._subscribe_callback
                self._subscribe_callback = None
                cb(True)

    @async_test
    @gen.engine
    def test_pub_sub(self):
        self._expect_messages({'subscribe': ('foo', 1),
                               'message': ('foo', 'bar'),
                               'unsubscribe': ('foo', 0)},
                              subscribe_callback=(yield gen.Callback('sub')))
        yield gen.Task(self.client.subscribe, 'foo')
        self.client.listen(self._handle_message,
                           exit_callback=(yield gen.Callback('listen')))
        yield gen.Wait('sub')
        yield gen.Task(self.publisher.publish, 'foo', 'bar')
        yield gen.Task(self.publisher.publish, 'foo', 'bar')
        yield gen.Task(self.publisher.publish, 'foo', 'bar')
        yield gen.Task(self.client.unsubscribe, 'foo')
        yield gen.Task(self.client.disconnect)
        yield gen.Wait('listen')

        self.assertEqual(self._message_count, 5)
        self.assertFalse(self.client.subscribed)
        self.stop()

    @async_test
    @gen.engine
    def test_unsubscribe(self):
        def on_message(*args, **kwargs):
            self._message_count += 1

        yield gen.Task(self.client.subscribe, 'foo')
        self.client.listen(on_message, (yield gen.Callback('listen')))
        self.assertTrue(self.client.subscribed)
        yield gen.Task(self.client.unsubscribe, 'foo')
        yield gen.Wait('listen')

        self.assertFalse(self.client.subscribed)
        yield gen.Task(self.client.subscribe, 'foo')
        self.client.listen(on_message, (yield gen.Callback('listen')))
        self.assertTrue(self.client.subscribed)
        yield gen.Task(self.client.unsubscribe, 'foo')
        yield gen.Wait('listen')

        self.assertFalse(self.client.subscribed)
        self.assertEqual(self._message_count, 4)
        self.stop()

    @async_test
    @gen.engine
    def test_pub_sub_multiple(self):
        self._expect_messages({'subscribe': ('foo', 1, 'boo', 2),
                               'message': ('foo', 'bar', 'boo', 'zar'),
                               'unsubscribe': ('foo', 0, 'boo', 0)},
                              subscribe_callback=(yield gen.Callback('sub')))
        yield gen.Task(self.client.subscribe, 'foo')
        self.client.listen(self._handle_message, (yield gen.Callback('listen')))
        yield gen.Wait('sub')
        yield gen.Task(self.client.subscribe, 'boo')
        yield gen.Task(self.publisher.publish, 'foo', 'bar')
        yield gen.Task(self.publisher.publish, 'boo', 'zar')

        yield gen.Task(self.client.unsubscribe, ['foo', 'boo'])
        yield gen.Wait('listen')

        self.assertEqual(self._message_count, 6)
        self.assertFalse(self.client.subscribed)
        self.stop()

    @async_test
    @gen.engine
    def test_pub_sub_multiple_2(self):
        self._expect_messages({'subscribe': ('foo', 1, 'boo', 2),
                               'message': ('foo', 'bar', 'boo', 'zar'),
                               'unsubscribe': ('foo', 0, 'boo', 0)},
                              subscribe_callback=(yield gen.Callback('sub')))

        yield gen.Task(self.client.subscribe, ['foo', 'boo'])
        self.client.listen(self._handle_message, (yield gen.Callback('listen')))
        yield gen.Wait('sub')

        yield gen.Task(self.publisher.publish, 'foo', 'bar')
        yield gen.Task(self.publisher.publish, 'boo', 'zar')

        yield gen.Task(self.client.unsubscribe, ['foo', 'boo'])
        yield gen.Wait('listen')

        self.assertEqual(self._message_count, 6)
        self.assertFalse(self.client.subscribed)
        self.stop()

    @async_test
    @gen.engine
    def test_pub_psub(self):
        self._expect_messages({'psubscribe': ('foo.*', 1),
                               'pmessage': ('foo.*', 'bar'),
                               'punsubscribe': ('foo.*', 0),
                               'unsubscribe': ('foo.*', 1)},
                              subscribe_callback=(yield gen.Callback('sub')))
        yield gen.Task(self.client.psubscribe, 'foo.*')
        self.client.listen(self._handle_message, (yield gen.Callback('listen')))
        yield gen.Wait('sub')
        yield gen.Task(self.publisher.publish, 'foo.1', 'bar')
        yield gen.Task(self.publisher.publish, 'bar.1', 'zar')
        yield gen.Task(self.client.punsubscribe, 'foo.*')

        yield gen.Wait('listen')

        self.assertEqual(self._message_count, 3)
        self.stop()


class DummyConnection(object):

    def __init__(self):
        self.messages = []
        self.session = namedtuple('FakeSession', ['is_closed'])(is_closed=False)

    def broadcast(self, clients, message):
        for client in clients:
            client.messages.append(message)

    def on_message(self, message):
        self.messages.append(message)


class SockJSSubscriberTestCase(RedisTestCase):

    def setUp(self):
        super(SockJSSubscriberTestCase, self).setUp()
        self.publisher = self._new_client()
        self.subscriber = SockJSSubscriber(self.client)

    def tearDown(self):
        if self.subscriber.is_subscribed():
            self.subscriber.close()
        try:
            self.publisher.connection.disconnect()
            del self.publisher
        except AttributeError:
            pass
        super(SockJSSubscriberTestCase, self).tearDown()

    @async_test
    @gen.engine
    def test_subscribe(self):
        broadcaster = DummyConnection()
        yield gen.Task(self.subscriber.subscribe, 'test.channel', broadcaster)
        data = {'foo': randint(0, 1000)}
        self.subscriber.publish('test.channel', data, client=self.publisher)

        yield gen.Task(self.pause)

        self.assertTrue(broadcaster.messages)
        self.assertEqual(broadcaster.messages[0], json.dumps(data))

        self.stop()

    @async_test
    @gen.engine
    def test_subscribe_unicode(self):
        broadcaster = DummyConnection()
        yield gen.Task(self.subscriber.subscribe, 'test.channel', broadcaster)
        data = {'foo': randint(0, 1000)}
        self.subscriber.publish('test.channel', data, client=self.publisher)

        yield gen.Task(self.pause)

        self.assertTrue(broadcaster.messages)
        self.assertEqual(broadcaster.messages[0], json.dumps(data))

        self.stop()

    @async_test
    @gen.engine
    def test_publish_unicode(self):
        broadcaster = DummyConnection()
        yield gen.Task(self.subscriber.subscribe, 'test.channel', broadcaster)
        data = 'лабуда-ерунда'
        self.publisher.publish('test.channel', data)

        yield gen.Task(self.pause)

        self.assertTrue(broadcaster.messages)
        self.assertEqual(broadcaster.messages[0], data)

        self.stop()

    @async_test
    @gen.engine
    def test_unsubscribe(self):
        broadcaster = DummyConnection()
        yield gen.Task(self.subscriber.subscribe, 'test.channel', broadcaster)
        self.subscriber.unsubscribe('test.channel', broadcaster)

        yield gen.Task(self.pause)

        self.assertFalse(broadcaster.messages)

        data = {'foo': randint(0, 1000)}
        yield gen.Task(self.subscriber.publish, 'test.channel', data,
                       client=self.publisher)

        yield gen.Task(self.pause)

        self.assertFalse(broadcaster.messages)

        self.stop()

    @async_test
    @gen.engine
    def test_unsubscribe_unicode(self):
        broadcaster = DummyConnection()
        yield gen.Task(self.subscriber.subscribe, 'test.channel', broadcaster)
        self.subscriber.unsubscribe('test.channel', broadcaster)

        yield gen.Task(self.pause)

        self.assertFalse(broadcaster.messages)

        data = {'foo': randint(0, 1000)}
        yield gen.Task(self.subscriber.publish, 'test.channel', data,
                       client=self.publisher)

        yield gen.Task(self.pause)

        self.assertFalse(broadcaster.messages)

        self.stop()

    @async_test
    @gen.engine
    def test_sequental_subscribe(self):
        broadcaster = DummyConnection()
        yield gen.Task(self.subscriber.subscribe, 'test.channel', broadcaster)
        yield gen.Task(self.subscriber.subscribe, 'test.channel2', broadcaster)
        self.subscriber.unsubscribe('test.channel2', broadcaster)
        self.subscriber.unsubscribe('test.channel', broadcaster)
        yield gen.Task(self.pause)
        yield gen.Task(self.subscriber.subscribe, 'test.channel', broadcaster)

        yield gen.Task(self.pause)

        self.assertFalse(broadcaster.messages)

        data = {'foo': randint(0, 1000)}
        yield gen.Task(self.subscriber.publish, 'test.channel', data,
                       client=self.publisher)

        yield gen.Task(self.pause)

        self.assertTrue(broadcaster.messages)

        self.stop()

    @async_test
    @gen.engine
    def test_subscribe_multiple(self):
        broadcaster = DummyConnection()
        broadcaster2 = DummyConnection()
        yield gen.Task(self.subscriber.subscribe, 'test.channel', broadcaster)
        yield gen.Task(self.subscriber.subscribe, 'test.channel2', broadcaster)
        yield gen.Task(self.subscriber.subscribe, 'test.channel', broadcaster2)
        data = {'foo': randint(0, 1000)}
        yield gen.Task(self.subscriber.publish, 'test.channel', data,
                       client=self.publisher)
        data2 = {'foo2': randint(0, 1000)}
        yield gen.Task(self.subscriber.publish, 'test.channel2', data2,
                       client=self.publisher)

        yield gen.Task(self.pause)

        msgs = broadcaster.messages + broadcaster2.messages
        self.assertEqual(len(msgs), 3)
        self.assertEqual(len(broadcaster.messages), 2)
        self.assertEqual(len(broadcaster2.messages), 1)
        self.assertEqual(broadcaster.messages[0], json.dumps(data))

        self.subscriber.unsubscribe('test.channel', broadcaster2)

        data2 = {'foo': randint(0, 1000)}

        yield gen.Task(self.subscriber.publish, 'test.channel', data2,
                       client=self.publisher)

        yield gen.Task(self.pause)

        msgs = broadcaster.messages + broadcaster2.messages
        self.assertEqual(len(msgs), 4)
        self.assertEqual(len(broadcaster.messages), 3)
        self.assertEqual(len(broadcaster2.messages), 1)
        self.assertEqual(broadcaster.messages[2], json.dumps(data2))

        self.stop()

    @async_test
    @gen.engine
    def test_subscribe_list(self):
        broadcaster = DummyConnection()
        broadcaster2 = DummyConnection()
        channels = ['test.channel', 'test.channel2']
        yield gen.Task(self.subscriber.subscribe, channels, broadcaster)
        yield gen.Task(self.subscriber.subscribe,
                       ('test.channel', ),
                       broadcaster2)
        data = {'foo': randint(0, 1000)}
        yield gen.Task(self.subscriber.publish, 'test.channel', data,
                       client=self.publisher)
        data2 = {'foo2': randint(0, 1000)}
        yield gen.Task(self.subscriber.publish, 'test.channel2', data2,
                       client=self.publisher)

        yield gen.Task(self.pause)

        msgs = broadcaster.messages + broadcaster2.messages
        self.assertEqual(len(msgs), 3)
        self.assertEqual(len(broadcaster.messages), 2)
        self.assertEqual(len(broadcaster2.messages), 1)
        self.assertEqual(broadcaster.messages[0], json.dumps(data))

        self.subscriber.unsubscribe('test.channel', broadcaster2)

        data2 = {'foo': randint(0, 1000)}

        yield gen.Task(self.subscriber.publish, 'test.channel', data2,
                       client=self.publisher)

        yield gen.Task(self.pause)

        msgs = broadcaster.messages + broadcaster2.messages
        self.assertEqual(len(msgs), 4)
        self.assertEqual(len(broadcaster.messages), 3)
        self.assertEqual(len(broadcaster2.messages), 1)
        self.assertEqual(broadcaster.messages[2], json.dumps(data2))

        self.stop()


class SocketIOSubscriberTestCase(SockJSSubscriberTestCase):

    def setUp(self):
        super(SocketIOSubscriberTestCase, self).setUp()
        self.subscriber = SocketIOSubscriber(self.client)
