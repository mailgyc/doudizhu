import logging
import random
from typing import List

from tornado.ioloop import IOLoop

from core.ai import AiPlayer
from net.protocol import Protocol as Pt

logger = logging.getLogger('ddz')


class Table(object):

    WAITING = 0
    PLAYING = 1
    END = 2
    CLOSED = 3

    def __init__(self):
        self.uid = Table.gen_id()
        self.players = [None, None, None]
        self.state = 0  # 0 waiting  1 playing 2 end 3 closed
        self.pokers: List[int] = []
        self.multiple = 1
        self.call_score = 0
        self.whose_turn = 0
        self.last_shot_seat = 0
        self.last_shot_poker = []
        self.room = 100
        IOLoop.current().call_later(1, self.ai_join)

    def ai_join(self):
        # for i in range(3 - self.size()):
        p1 = AiPlayer(11, 'AI-1')
        p1.send([Pt.REQ_JOIN_TABLE, self.uid])

        p2 = AiPlayer(12, 'AI-2')
        p2.send([Pt.REQ_JOIN_TABLE, self.uid])
        logger.info('TABLE[%d] AI JOIN', self.uid)

        self.sync_table()

    def sync_table(self):
        response = [Pt.RSP_JOIN_TABLE, self.uid, [g.uid if g else -1 for g in self.players]]
        for player in self.players:
            if player:
                player.send(response)
        if self.size() == 3:
            self.deal_poker()

    def deal_poker(self):
        if not all(p and p.ready for p in self.players):
            return

        self.state = 1
        self.pokers = [i for i in range(54)]
        random.shuffle(self.pokers)
        for i in range(51):
            self.players[i % 3].pokers.append(self.pokers.pop())

        self.whose_turn = random.randint(0, 2)
        player_id = self.players[self.whose_turn].uid
        for p in self.players:
            response = [Pt.RSP_DEAL_POKER, player_id, p.pokers]
            p.send(response)
            logger.info('Player[%d] deal[%s]', p.uid, str(p.pokers))
        logger.info("Player[%d %d]'s turn", player_id, self.whose_turn)

    def go_next_turn(self):
        self.whose_turn += 1
        if self.whose_turn == 3:
            self.whose_turn = 0

    def calc_coin(self, winner):
        self.state = 2
        coins = []
        tax = 100
        for p in self.players:
            p.ready = False
            coin = self.room * p.rank * self.call_score * self.multiple
            if p.rank == winner.rank:
                coins.append(coin - tax)
            else:
                coins.append(-coin - tax)
        return coins

    def add(self, player):
        for i, p in enumerate(self.players):
            if not p:
                player.seat = i
                self.players[i] = player
                logger.info('Table[%d] add Player[%d]', self.uid, player.uid)
                return True
        logger.error('Player[%d] join a full Table[%d]', player.pid, self.uid)
        return False

    def remove(self, player):
        for i, p in enumerate(self.players):
            if p and p.pid == player.pid:
                self.players[i] = None
        else:
            logger.error('Player[%d] not in Table[%d]', player.pid, self.uid)

        if all(p is None for p in self.players):
            self.state = 3
            logger.error('Table[%d] close', self.uid)
            return True
        return False

    def size(self):
        return sum([p is not None for p in self.players])

    def __str__(self):
        return str(self.uid)

    counter = 0

    @classmethod
    def gen_id(cls):
        cls.counter += 1
        return cls.counter

