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
        self.table: Table = []
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

        call_end = score == 3 or self.table.all_called()
        if not call_end:
            self.table.whose_turn = next_seat
        if score > 0:
            self.table.last_shot_seat = self.seat
        if score > self.table.max_call_score:
            self.table.max_call_score = score
            self.table.max_call_score_turn = self.seat

        response = [Pt.RSP_CALL_SCORE, self.uid, score, call_end]
        for p in self.table.players:
            p.send(response)

        if call_end:
            self.table.call_score_end()

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

        if not self.hand_pokers:
            self.table.on_game_over(self)

    def join_table(self, t):
        self.ready = True
        self.table = t
        t.on_join(self)

    def leave_table(self):
        self.ready = False
        if self.table:
            self.table.on_leave(self)
        # self.table = None

    def __repr(self):
        return self.__str__()

    def __str__(self):
        return self.uid + '-' + self.name
