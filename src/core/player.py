import logging
from typing import List

from tornado.websocket import WebSocketHandler

from core import rule
from net.protocol import Protocol as Pt

logger = logging.getLogger('ddz')

FARMER = 1
LANDLORD = 2


class Player(object):
    def __init__(self, uid: int, name: str, socket: WebSocketHandler = None):
        from core.table import Table
        self.uid = uid
        self.name = name
        self.socket = socket
        self.room = None
        self.table: Table = None
        self.ready = False
        self.seat = 0
        self.is_called = False
        self.role = FARMER
        self.hand_pokers: List[int] = []

    def send(self, packet):
        self.socket.write_message(packet)

    def handle_call_score(self, score):
        if 0 < score < self.table.call_score:
            logger.warning('Player[%d] CALL SCORE[%d] CHEAT', self.uid, score)
            return

        if score > 3:
            logger.warning('Player[%d] CALL SCORE[%d] CHEAT', self.uid, score)
            return

        self.is_called = True

        next_seat = (self.seat + 1) % 3
        call_end = score == 3 or self.table.players[next_seat].is_called
        if not call_end:
            self.table.whose_turn = next_seat
        if score > 0:
            self.table.last_shot_seat = self.seat
            self.table.call_score = score

        response = [Pt.RSP_CALL_SCORE, self.uid, score, call_end]
        for p in self.table.players:
            p.send(response)

        if call_end:
            self.table.call_score_end(score)

    def handle_shot_poker(self, pokers):
        if pokers:
            if not rule.is_contains(self.hand_pokers, pokers):
                logger.warning('Player[%d] play non-exist poker', self.uid)
                return

            if self.table.last_shot_seat != self.seat and rule.compare_poker(pokers, self.table.last_shot_poker) < 0:
                logger.warning('Player[%d] play small than last shot poker', self.uid)
                return

        self.table.go_next_turn()
        if pokers:
            self.table.last_shot_seat = self.seat
            self.table.last_shot_poker = pokers
            for p in pokers:
                self.hand_pokers.remove(p)

        response = [Pt.RSP_SHOT_POKER, self.uid, pokers]
        for p in self.table.players:
            p.send(response)
        logger.info('Player[%d] shot[%s]', self.uid, str(pokers))

        self.handle_game_over()

    def handle_game_over(self):
        if self.hand_pokers:
            return
        response = [Pt.REQ_GAME_OVER, self.uid, self.table.calc_coin(self)]
        for p in self.table.players:
            p.send(response)
        logger.info('Table[%d] over[%d]', self.table.uid, self.uid)

    def join_table(self, t):
        t.add(self)
        self.ready = True
        self.table = t

    def leave_table(self):
        self.ready = False
        if self.table:
            self.table.remove(self)
            logger.info('Player[%d] leave Table[%d]', self.uid, self.table.uid)

    def __repr(self):
        return self.__str__()

    def __str__(self):
        return self.uid + '-' + self.name
