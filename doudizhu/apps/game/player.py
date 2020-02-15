from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

from tornado.websocket import WebSocketHandler

from .protocol import Protocol as Pt
from .rule import rule

if TYPE_CHECKING:
    from .room import Room

logger = logging.getLogger(__file__)

FARMER = 1
LANDLORD = 2


class Player(object):
    def __init__(self, uid: int, name: str, socket: WebSocketHandler = None):
        self.uid = uid
        self.name = name
        self.socket = socket
        self.room: Optional[Room] = None
        self.ready = False
        self.seat = 0
        self.is_called = False
        self.role = FARMER
        self.hand_pokers: List[int] = []

    def reset(self):
        self.ready = False
        self.is_called = False
        self.role = FARMER
        self.hand_pokers: List[int] = []
        self.send([Pt.RSP_RESTART])

    def send(self, packet):
        self.socket.write_message(packet)

    def handle_call_score(self, score):
        if 0 < score < self.room.call_score:
            logger.warning('Player[%d] CALL SCORE[%d] CHEAT', self.uid, score)
            return

        if score > 3:
            logger.warning('Player[%d] CALL SCORE[%d] CHEAT', self.uid, score)
            return

        self.is_called = True

        next_seat = (self.seat + 1) % 3

        call_end = score == 3 or self.room.all_called()
        if not call_end:
            self.room.whose_turn = next_seat
        if score > 0:
            self.room.last_shot_seat = self.seat
        if score > self.room.max_call_score:
            self.room.max_call_score = score
            self.room.max_call_score_turn = self.seat
        response = [Pt.RSP_CALL_SCORE, self.uid, score, call_end]
        for p in self.room.players:
            p.send(response)

        if call_end:
            self.room.call_score_end()

    def handle_shot_poker(self, pokers):
        if pokers:
            if not rule.is_contains(self.hand_pokers, pokers):
                logger.warning('Player[%d] play non-exist poker', self.uid)
                return

            if self.room.last_shot_seat != self.seat and rule.compare_poker(pokers, self.room.last_shot_poker) < 0:
                logger.warning('Player[%d] play small than last shot poker', self.uid)
                return
        if pokers:
            self.room.history[self.seat] += pokers
            self.room.last_shot_seat = self.seat
            self.room.last_shot_poker = pokers
            for p in pokers:
                self.hand_pokers.remove(p)

        if self.hand_pokers:
            self.room.go_next_turn()

        response = [Pt.RSP_SHOT_POKER, self.uid, pokers]
        for p in self.room.players:
            p.send(response)
        logger.info('Player[%d] shot[%s]', self.uid, str(pokers))

        if not self.hand_pokers:
            self.room.on_game_over(self)
            return

    def join_room(self, room: Room):
        self.ready = True
        self.room = room
        room.arrange_seat(self)

    def leave_room(self):
        self.ready = False
        if self.room:
            self.room.on_leave(self)
        self.room = None

    def __repr(self):
        return self.__str__()

    def __str__(self):
        return f'{self.uid}-{self.name}'
