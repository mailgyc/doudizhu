import logging
import random

import tornado.escape
import tornado.ioloop
import tornado.websocket

logger = logging.getLogger()


class Table(object):
    def __init__(self):
        self.pid = Table.gen_id()
        self.players = [None, None, None]
        self.state = 0  # 0 waiting  1 playing 2 end 3 closed
        self.pokers = []
        self.multiple = 1
        self.callscore = 0
        self.whoseTurn = 0
        self.last_shot_seat = 0;
        self.last_shot_poker = [];
        self.room = 100
        tornado.ioloop.IOLoop.current().add_callback(self.update)

    def calc_coin(self, winner):
        self.state = 2
        coins = []
        tax = 100
        for p in self.players:
            p.ready = False
            coin = self.room * p.rank * self.callscore * self.multiple
            if p.rank == winner.rank:
                coins.append(coin - tax)
            else:
                coins.append(-coin - tax)
        return coins

    def update(self):
        logger.info('table[%d] update', self.pid)

    def add(self, player):
        for i, p in enumerate(self.players):
            if not p:
                player.seat = i
                self.players[i] = player
                logger.info('Table[%d] add Player[%d]', self.pid, player.pid)
                return True
        logger.error('Player[%d] join a full Table[%d]', player.pid, self.pid)
        return False

    def remove(self, player):
        for i, p in enumerate(self.players):
            if p and p.pid == player.pid:
                self.players[i] = None
        else:
            logger.error('Player[%d] not in Table[%d]', player.pid, self.pid)

        if all(p == None for p in self.players):
            self.state = 3
            logger.error('Table[%d] close', self.pid)
            return True
        return False

    def size(self):
        return 3 - self.players.count(None)

    def deal_poker(self):
        if not all(p and p.ready for p in self.players):
            return

        self.state = 1
        self.pokers = [i for i in range(54)]
        random.shuffle(self.pokers)
        for i in range(51):
            self.players[i % 3].pokers.append(self.pokers.pop())

        self.whoseTurn = random.randint(0, 2)
        for p in self.players:
            p.dealPoker()

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
