import time
import socket

from tornado import gen
from tornado.escape import to_basestring
from tornado.tcpserver import TCPServer

from tornado.testing import AsyncTestCase

import tornadoredis
from tornadoredis.exceptions import ConnectionError
from tornadoredis.tests.redistest import async_test


class DisconnectingRedisServer(TCPServer):

    def disconnect(self):
        # Using a single stream for testing
        stream = self._stream
        self._stream = None
        try:
            stream.socket.shutdown(socket.SHUT_RDWR)
            stream.close()
        except socket.error:
            pass

    @gen.engine
    def handle_stream(self, stream, address):
        self.selected_db = 0
        self._stream = stream
        CRLF = b'\r\n'
        n_args = yield gen.Task(stream.read_until, CRLF)
        n_args = to_basestring(n_args)
        while n_args and n_args[0] == '*':
            yield gen.Task(stream.read_until, CRLF)
            command = yield gen.Task(stream.read_until, CRLF)
            command = to_basestring(command)
            # Read command arguments
            arg_num = int(n_args.strip()[1:]) - 1
            if arg_num > 0:
                for __ in range(0, arg_num):
                    # read the $N line
                    yield gen.Task(stream.read_until, CRLF)
                    # read the argument line
                    arg = yield gen.Task(stream.read_until, CRLF)
                    arg = to_basestring(arg)
                    if command == 'SELECT\r\n':
                        self.selected_db = int(arg.strip())
            stream.write(b'+OK\r\n')
            # Read the next command
            n_args = yield gen.Task(stream.read_until, CRLF)
            n_args = to_basestring(n_args)


class DisconnectTestCase(AsyncTestCase):
    test_db = 9
    test_port = 6380

    def setUp(self):
        #self._server_io_loop = IOLoop()
        # self._server_io_loop
        super(DisconnectTestCase, self).setUp()
        self._server = DisconnectingRedisServer(io_loop=self.io_loop)
        self._server.listen(self.test_port)
        self.server_running = True
        self.client = self._new_client()
        self.client.flushdb()

    def tearDown(self):
        try:
            self.client.connection.disconnect()
            del self.client
        except AttributeError:
            pass
        if self.server_running:
            self._server.stop()
        super(DisconnectTestCase, self).tearDown()

    def _new_client(self):
        client = tornadoredis.Client(io_loop=self.io_loop,
                                     port=self.test_port,
                                     selected_db=self.test_db)
        # client.connection.connect()
        # client.select(self.test_db)
        return client

    def test_disconnect(self):
        def _disconnect_and_send_a_command():
            self.client.set('foo', 'bar', callback=self.stop)
            self.wait()
            self._server.disconnect()
            self._server.stop()
            self.server_running = False
            self.client.set('foo', 'bar', callback=self.stop)
            self.wait()
        self.assertRaises(ConnectionError, _disconnect_and_send_a_command)

    def _sleep(self):
        self.io_loop.add_timeout(time.time() + 0.1, self.stop)
        self.wait()

    def test_reconnect(self):
        self.client.set('foo', 'bar', callback=self.stop)
        self.wait()
        self._server.disconnect()
        self._sleep()
        self.client.set('foo', 'bar', callback=self.stop)
        self.wait()

    def test_reconnect_db(self):
        # let select/flushdb happen
        self._sleep()

        # check selected db
        self.assertEqual(self.test_db, self._server.selected_db)

        # stop server
        self._server.disconnect()
        self._server.stop()
        self.server_running = False
        self._sleep()

        # let command fail
        try:
            self.client.set('foo', 'bar', callback=self.stop)
            self.wait()
        except ConnectionError:
            pass

        # restart server
        self._server = DisconnectingRedisServer(io_loop=self.io_loop)
        self._server.listen(self.test_port)
        self.server_running = True
        self._sleep()

        # reissue command
        self.client.set('foo', 'bar', callback=self.stop)
        self.wait()

        # check selected db
        self.assertEqual(self.test_db, self._server.selected_db)

    @async_test
    @gen.engine
    def test_disconnect_when_subscribed(self):
        cb_disconnect = (yield gen.Callback('disconnect'))

        def handle_message(msg):
            print(msg)
            if msg.kind == 'disconnect':
                cb_disconnect(msg.channel)

        yield gen.Task(self.client.subscribe, 'foo')
        self.client.listen(handle_message)

        self._server.disconnect()

        res = yield gen.Wait('disconnect')
        self.assertEqual(res, set(['foo']))
        self.assertFalse(self.client.subscribed)

        self.stop()
