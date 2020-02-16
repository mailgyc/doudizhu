from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from tornado.ioloop import IOLoop

from ..player import Player
from ..protocol import Protocol as Pt
from ..rule import rule

if TYPE_CHECKING:
    from ..room import Room


class RobotPlayer(Player):

    def __init__(self, uid: int, username: str, room: Room):
        super().__init__(uid, username, None)
        self.room = room

    @property
    def allow_robot(self) -> bool:
        return True

    def to_server(self, packet):
        IOLoop.current().add_callback(self.on_message, packet)

    def write_message(self, packet):
        code = packet[0]
        if code == Pt.RSP_JOIN_ROOM:
            IOLoop.current().add_callback(self.to_server, [Pt.REQ_READY])
        elif code == Pt.RSP_DEAL_POKER:
            if self.uid == packet[1]:
                self.auto_call_score()
        elif code == Pt.RSP_CALL_SCORE:
            if self.room.turn_player == self:
                # caller = packet[1]
                # score = packet[2]
                call_end = packet[3]
                if not call_end:
                    self.auto_call_score()
                else:
                    self.auto_shot_poker()
        elif code == Pt.RSP_SHOW_POKER:
            if self.room.turn_player == self:
                self.auto_shot_poker()
        elif code == Pt.RSP_SHOT_POKER:
            if self.room.turn_player == self and self.hand_pokers:
                self.auto_shot_poker()
        elif code == Pt.RSP_GAME_OVER:
            IOLoop.current().add_callback(self.to_server, [Pt.REQ_RESTART])
            IOLoop.current().add_callback(self.to_server, [Pt.REQ_READY])

    def auto_call_score(self, score=0):
        # millis = random.randint(1000, 2000)
        # score = random.randint(min_score + 1, 3)
        packet = [Pt.REQ_CALL_SCORE, self.room.call_score + 1]
        IOLoop.current().add_callback(self.to_server, packet)

    def auto_shot_poker(self):
        pokers = []
        if not self.room.last_shot_poker or self.room.last_shot_seat == self.seat:
            pokers.append(self.hand_pokers[0])
        else:
            pokers = rule.cards_above(self.hand_pokers, self.room.last_shot_poker)

        packet = [Pt.REQ_SHOT_POKER, pokers]
        IOLoop.current().call_later(1, self.to_server, packet)
