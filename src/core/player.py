import logging
from typing import List

import tornado.escape
from tornado.websocket import WebSocketHandler

import core
from core import rule
from net.protocol import Protocol as Pt

logger = logging.getLogger('ddz')

FARMER = 1
LANDLORD = 2


class Player(object):
    def __init__(self, uid: int, name: str, socket: WebSocketHandler=None):
        self.uid = uid
        self.name = name
        self.socket = socket
        self.table: core.Table = None
        self.ready = False
        self.seat = 0
        self.is_called = False
        self.role = FARMER
        self.pokers: List[int] = []

    def send(self, packet):
        self.socket.write_message(packet)

    def shot_poker(self, pokers):

        if not rule.is_contains(self.pokers, pokers):
            logger.warning('Player[%d] play non-exist poker', self.uid)
            return

        if self.table.last_shot_seat != self.seat and rule.compare(pokers, self.table.last_shot_poker) < 0:
            logger.warning('Player[%d] play small than last shot poker', self.uid)
            return

        self.table.go_next_turn()
        self.table.last_shot_seat = self.seat
        self.table.last_shot_poker = pokers

        for p in pokers:
            self.pokers.remove(p)
        game_end = len(self.pokers) == 0

        response = [Pt.RSP_SHOT_POKER, self.uid, pokers, game_end]
        for p in self.table.players:
            p.send(response)
        logger.info('Player[%d] shot[%s]', self.uid, str(pokers))

        if game_end:
            response = [Pt.REQ_GAME_OVER, self.uid, self.table.calc_coin(self.player)]
            for p in self.table.players:
                p.send(response)
            logger.info('Table[%d] over[%d]', self.table.uid, self.uid)

    def no_shot(self):
        self.table.go_next_turn()
        response = [Pt.RSP_NO_SHOT, self.uid]
        for p in self.table.players:
            p.send(response)

    def handle_call_score(self, score):

        self.is_called = True

        next_seat = (self.seat + 1) % 3
        call_end = score == 3 or self.table.players[next_seat].is_called

        response = [Pt.RSP_CALL_SCORE, self.uid, score, call_end]
        message = tornado.escape.json_encode(response)
        for g in self.table.players:
            g.send(message)

        logger.info('Player[%d] call score[%d]', self.uid, score)
        if call_end:
            if score == 0:
                self.table.shot_poker()
            else:
                self.role = 2
                self.table.call_score = score
                response = [Pt.RSP_SHOW_POKER, self.table.pokers]
                message = tornado.escape.json_encode(response)
                for p in self.table.players:
                    p.send(message)
                logger.info('Player[%d] is landlord[%s]', self.uid, str(self.table.pokers))
        else:
            self.table.whoseTurn = next_seat

    def join_table(self, t):
        t.add(self)
        self.ready = True
        self.table = t

    def __str__(self):
        return self.uid + '-' + self.name
