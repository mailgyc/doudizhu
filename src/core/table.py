import logging
import random
from typing import List

from tornado.ioloop import IOLoop

from core.robot import AiPlayer
from net.protocol import Protocol as Pt

logger = logging.getLogger('ddz')


class Table(object):

    WAITING = 0
    PLAYING = 1
    END = 2
    CLOSED = 3

    def __init__(self, room):
        self.uid = Table.gen_id()
        self.players = [None, None, None]
        self.state = 0  # 0 waiting  1 playing 2 end 3 closed
        self.pokers: List[int] = []
        self.multiple = 1
        self.call_score = 0
        self.whose_turn = 0
        self.last_shot_seat = 0
        self.last_shot_poker = []
        self.room = room
        if room.allow_robot:
            IOLoop.current().call_later(0.1, self.ai_join, nth=1)

    def ai_join(self, nth=1):
        size = self.size()
        if size == 0 or size == 3:
            return

        if size == 2 and nth == 1:
            IOLoop.current().call_later(1, self.ai_join, nth=2)

        p1 = AiPlayer(11, 'AI-1', self.players[0])
        p1.to_server([Pt.REQ_JOIN_TABLE, self.uid])

        if size == 1:
            p2 = AiPlayer(12, 'AI-2', self.players[0])
            p2.to_server([Pt.REQ_JOIN_TABLE, self.uid])

    def sync_table(self):
        ps = []
        for p in self.players:
            if p:
                ps.append((p.uid, p.name))
            else:
                ps.append((-1, ''))

        response = [Pt.RSP_JOIN_TABLE, self.uid, ps]
        for player in self.players:
            if player:
                player.send(response)

    def deal_poker(self):
        # if not all(p and p.ready for p in self.players):
        #     return

        self.state = 1
        self.pokers = [i for i in range(54)]
        random.shuffle(self.pokers)
        for i in range(51):
            self.players[i % 3].hand_pokers.append(self.pokers.pop())

        self.whose_turn = random.randint(0, 2)
        for p in self.players:
            p.hand_pokers.sort()
            response = [Pt.RSP_DEAL_POKER, self.turn_player.uid, p.hand_pokers]
            p.send(response)

    def call_score_end(self, score):
        self.call_score = score
        self.turn_player.role = 2
        self.turn_player.hand_pokers += self.pokers
        response = [Pt.RSP_SHOW_POKER, self.turn_player.uid, self.pokers]
        for p in self.players:
            p.send(response)
        logger.info('Player[%d] IS LANDLORD[%s]', self.turn_player.uid, str(self.pokers))

    def go_next_turn(self):
        self.whose_turn += 1
        if self.whose_turn == 3:
            self.whose_turn = 0

    @property
    def turn_player(self):
        return self.players[self.whose_turn]

    def calc_coin(self, winner):
        self.state = 2
        coins = []
        tax = 100
        for p in self.players:
            p.ready = False
            coin = self.room.entrance_fee * self.call_score * self.multiple
            if p == winner:
                coins.append(coin - tax)
            else:
                coins.append(-coin - tax)
        return coins

    def handle_chat(self, player, msg):
        response = [Pt.RSP_CHAT, player.uid, msg]
        for p in self.players:
            p.send(response)

    def add(self, player):
        for i, p in enumerate(self.players):
            if not p:
                player.seat = i
                self.players[i] = player
                return True
        logger.error('Player[%d] JOIN Table[%d] FULL', player.pid, self.uid)
        return False

    def remove(self, player):
        for i, p in enumerate(self.players):
            if p and p.pid == player.pid:
                self.players[i] = None
        else:
            logger.error('Player[%d] NOT IN Table[%d]', player.pid, self.uid)

        if all(p is None for p in self.players):
            self.state = 3
            logger.error('Table[%d] close', self.uid)
            return True
        return False

    def size(self):
        return sum([p is not None for p in self.players])

    def __str__(self):
        return '[{}: {}]'.format(self.uid, self.players)

    counter = 0

    @classmethod
    def gen_id(cls):
        cls.counter += 1
        return cls.counter

