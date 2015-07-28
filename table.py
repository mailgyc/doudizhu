import logging
import uuid
import tornado.escape
import tornado.ioloop
import tornado.websocket

logger = logging.getLogger()

class Player(object):

    def __init__(self, table):
        self.pid = next(Player.gen_id())
        self.socket = None
        self.table = table

    def send(self, packet):
        self.socket.write_message(packet)

    def recv(self, message):
        self.send(message)
        #if packet.pid == 10:
        #    passd

    def open(self, socket):
        self.socket = socket

    counter = 1000
    @classmethod
    def gen_id(cls):
        cls.counter +=1
        return cls.counter

class Table(object):

    def __init__(self):
        self.pid = Table.gen_id()
        self.players = []
        self.closed = False
        tornado.ioloop.IOLoop.current().add_callback(self.update)

    def update(self):
        logger.info('table[%d] update', self.pid)

    def add(self, player):
        self.players.append(player)

    def remove(self, player):
        self.players.remove(player)
        if len(self.players) == 0:
            self.closed = True
            return True
        return False

    def size(self):
        return len(self.players)

    counter = 0
    @classmethod
    def gen_id(cls):
        cls.counter += 1
        return cls.counter

if __name__ == '__main__':
    t = Table()
    print(t.pid)
    t = Table()
    print(t.pid)
    t = Table()
    print(t.pid)
    t = Table()
    print(t.pid)




