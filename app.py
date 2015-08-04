import logging
import os.path
import tornado.escape
import tornado.ioloop
import tornado.web
import tornado.websocket
from table import Table, Player

from tornado.options import define, options

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


define('port', default=8000, help='run on the given port', type=int)
define('debug', default=True, help='run in debug mode')

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/socket", SocketHandler),
        ]
        settings = dict(
            cookie_secret = "ddz-601743bb-3c82-4fe6-b27f-a1159f04c4f",
            static_path  = os.path.join(os.path.dirname(__file__), 'static'),
            xsrf_cookies = True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')

class SocketHandler(tornado.websocket.WebSocketHandler):
    tableList = []

    def __init__(self, *args, **kwargs):
        tornado.websocket.WebSocketHandler.__init__(self, *args, **kwargs)
        #super().__init__(*args, **kwargs)
        self.player = Player()

    def get_compression_options(self):
        return {}

    def open(self):
        logger.info('player[%d] open', self.player.pid)
        self.player.open(self)

    def on_message(self, message):
        logger.info('got message %s', message)
        request = tornado.escape.json_decode(message)

        if request[0] == 1: # player info
            response = [2, self.player.pid]
            self.write_message(tornado.escape.json_encode(response))
        elif request[0] == 11: # request table list
            self.sendTableList()
        elif request[0] == 13: # request join table
            table_id = request[1]
            self.sendJoinTable(table_id)
        elif request[0] == 15: # fast join table
            self.sendFastJoinTable()
        else:
            self.player.recv(request)
        #SocketHandler.send_updates(message)

    def sendTableList(self):
        response = [12, []]
        for t in SocketHandler.tableList:
            response[1].append(t.pid)
        self.write_message(tornado.escape.json_encode(response))

    def sendJoinTable(self, table_id):
        t = SocketHandler.find_table_by_id(table_id)
        if not t:
            self.player.join_table(t)
            logger.info('Player[%d] create Table[%d]', self.player.pid, self.player.seat, t.pid)

        self.syncTable(t, 14)

        logger.info('Player[%d] join table[%d]', self.player.pid, t.pid)

    def sendFastJoinTable(self):
        t = SocketHandler.find_wait_table();
        self.player.join_table(t)

        self.syncTable(t, 16)

        logger.info('Player[%d] fast join table[%d]', self.player.pid, t.pid)

    def syncTable(self, t, opcode):
        response = [opcode, t.pid, [p.pid if p else -1 for p in t.players]]
        for p in t.players:
            if p:
                p.send(response)
        if t.size() == 3:
            t.dealPoker()

    def on_close(self):
        logger.info('Player[%d] close', self.player.pid)

        if self.player.table and self.player.table.remove(self.player):
            logger.info('Table[%d] close', self.player.table.pid)
            SocketHandler.tableList.remove(self.player.table)

    @classmethod
    def find_table_by_id(cls, pid):
        for t in cls.tableList:
            if t.pid == pid:
                return t
        return None

    @classmethod
    def find_wait_table(cls):
        for t in cls.tableList:
            if t.size() < 3:
               return t
        t = Table()
        cls.tableList.append(t)
        return t

    @classmethod
    def send_updates(cls, chat):
        logger.info('sending message to %d waiters', len(cls.waiters))
        for waiter in cls.waiters:
            try:
                waiter.write_message('tornado:' + chat)
            except:
                logging.error('Error sending message', exc_info=True)


def main():
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()

if  __name__ == '__main__':
    main()


