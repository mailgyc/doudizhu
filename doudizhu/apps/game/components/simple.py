from __future__ import annotations

from random import randint
from typing import TYPE_CHECKING

from tornado.ioloop import IOLoop

from ..player import Player
from ..protocol import Protocol as Pt
from ..rule import rule

if TYPE_CHECKING:
    from ..room import Room


class RobotPlayer(Player):

    def __init__(self, uid: int, username: str, room: Room):
        super().__init__(uid, username)
        self.room = room

    @property
    def allow_robot(self) -> bool:
        return True

    def to_server(self, packet):
        IOLoop.current().add_callback(self.on_message, packet)

    def write_message(self, packet):
        IOLoop.current().add_callback(self._write_message, packet)

    def _write_message(self, packet):
        code = packet[0]
        if code == Pt.RSP_JOIN_ROOM:
            self.auto_ready()
        elif code == Pt.RSP_DEAL_POKER:
            if self.uid == packet[1]['uid']:
                self.auto_call_score()
        elif code == Pt.RSP_CALL_SCORE:
            if self.room.turn_player == self:
                landlord = packet[1]['landlord']
                if landlord == -1:
                    self.auto_call_score()
                elif self.room.turn_player == self:
                    IOLoop.current().call_later(1, self.auto_shot_poker)
        elif code == Pt.RSP_SHOT_POKER:
            if self.room.turn_player == self and self.hand_pokers:
                self.auto_shot_poker()
        elif code == Pt.RSP_GAME_OVER:
            self.auto_ready()

    def auto_ready(self):
        IOLoop.current().add_callback(self.to_server, [Pt.REQ_READY, {'ready': 1}])

    def auto_call_score(self):
        packet = [Pt.REQ_CALL_SCORE, {'rob': randint(0, 1)}]
        IOLoop.current().call_later(1.5, self.to_server, packet)

    def auto_shot_poker(self):
        if not self.room.last_shot_poker or self.room.last_shot_seat == self.seat:
            pokers = rule.find_best_shot(self.hand_pokers)
        else:
            follow = not self.room.players[self.room.last_shot_seat].landlord == 1
            pokers = rule.cards_above(self.hand_pokers, self.room.last_shot_poker, follow)

        packet = [Pt.REQ_SHOT_POKER, {'pokers': pokers}]
        IOLoop.current().call_later(2, self.to_server, packet)
