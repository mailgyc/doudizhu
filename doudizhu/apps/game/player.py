from __future__ import annotations

import functools
import logging
from enum import IntEnum
from random import randint
from typing import TYPE_CHECKING, List, Optional, Dict, Any

from .protocol import Protocol as Pt
from .rule import rule

if TYPE_CHECKING:
    from .room import Room
    from .views import SocketHandler

logger = logging.getLogger(__file__)


def shot_turn(method):
    @functools.wraps(method)
    def wrapper(player, *args, **kwargs):
        if player.room and player.room.whose_turn == player.seat:
            method(player, *args, **kwargs)
        else:
            player.write_error('TURN ERROR')

    return wrapper


class State(IntEnum):
    INIT = 0
    WAITING = 1
    CALL_SCORE = 2
    PLAYING = 3
    GAME_OVER = 4


class Player(object):

    def __init__(self, uid: int, name: str):
        self.uid = uid
        self.name = name
        self.sex = randint(0, 1)
        self.point = 1000
        self.room: Optional[Room] = None
        self.seat = -1
        self.state = State.INIT

        self._ready = 0
        self._leave = 0

        self.rob = -1
        self.landlord = 0
        self._hand_pokers: List[int] = []

        self.socket: Optional[SocketHandler] = None

    def restart(self):
        self._ready = 0
        self._hand_pokers: List[int] = []

        self.rob = -1
        self.landlord = 0
        self.state = State.WAITING

    def sync_data(self, real=True) -> Dict[str, str]:
        return {
            'uid': self.uid,
            'name': self.name,
            'sex': self.sex,
            'icon': '',
            'ready': self.ready,
            'rob': self.rob,
            'leave': self._leave,
            'landlord': self.landlord,
            'point': self.point,
            'pokers': self.hand_pokers if real else [0] * len(self.hand_pokers),
        }

    def push_pokers(self, pokers: List[int]):
        self._hand_pokers += pokers

        def compare_single_poker(poker: int):
            if poker == 53 or poker == 54:
                return poker
            poker = poker % 13
            if poker <= 2:
                return poker + 13
            return poker
        self._hand_pokers.sort(key=compare_single_poker)

    @property
    def hand_pokers(self) -> List[int]:
        return self._hand_pokers

    def on_message(self, code: int, packet: Dict[str, Any]):
        if self.is_left():
            if self.handle_leave(code, packet):
                return

        if code == Pt.REQ_LEAVE_ROOM:
            self.on_disconnect()
            return

        if self.state == State.INIT:
            self.handle_init(code, packet)
        elif self.state == State.WAITING:
            self.handle_waiting(code, packet)
        elif self.state == State.CALL_SCORE:
            self.handle_call_score(code, packet)
        elif self.state == State.PLAYING:
            self.handle_playing(code, packet)
        elif self.state == State.GAME_OVER:
            self.handle_game_over(code, packet)

    def on_disconnect(self):
        self.set_left()

    def on_timeout(self):
        if not self.is_left():
            return
        if self.state == State.CALL_SCORE:
            self.on_message(Pt.REQ_CALL_SCORE, {'rob': 0})
        elif self.state == State.PLAYING:
            if not self.room.last_shot_poker or self.room.last_shot_seat == self.seat:
                self.on_message(Pt.REQ_SHOT_POKER, rule.find_best_shot(self.hand_pokers))
            else:
                self.on_message(Pt.REQ_SHOT_POKER, {'pokers': []})

    def handle_leave(self, code: int, packet: Dict[str, Any]):
        from .storage import Storage
        if code == Pt.REQ_JOIN_ROOM:
            self.set_left(0)
            room_id, level = packet.get('room', -1), packet.get('level', 1)
            if room_id == -1:
                self.restart()
                self.state = State.INIT
                if self.room:
                    self.room.on_leave(self)
                    self.room = None
                return False

            room = Storage.find_room(room_id, level, self.allow_robot)
            if room.room_id == room_id:
                self.room.sync_room()
                logger.info('PLAYER[%s] REJOIN ROOM[%d]', self.uid, room.room_id)
            else:
                self.write_error('Room[%s] Not Found' % room_id)
        return True

    def handle_init(self, code: int, packet: Dict[str, Any]):
        from .storage import Storage
        if code == Pt.REQ_JOIN_ROOM:
            room_id, level = packet.get('room', -1), packet.get('level', 1)
            room = Storage.find_room(room_id, level, self.allow_robot)

            self.state = State.WAITING
            if self.join_room(room):
                self.room.sync_room()
            logger.info('PLAYER[%s] JOIN ROOM[%d]', self.uid, room.room_id)

            if room.is_full():
                Storage.on_room_changed(room)
                logger.info('ROOM[%s] FULL[%s]', room.room_id, room.players)
        else:
            self.write_error('ERROR STATE[%s]' % self.state)

    def handle_waiting(self, code: int, packet: Dict[str, Any]):
        if code == Pt.REQ_READY:
            self.ready = packet.get('ready')
            if self.room.is_ready():
                self.change_state(State.CALL_SCORE)
                self.room.on_deal_poker()
        else:
            self.write_error('STATE[%s]' % self.state)

    @shot_turn
    def handle_call_score(self, code: int, packet: Dict[str, Any]):
        if code == Pt.REQ_CALL_SCORE:
            self.rob = packet.get('rob')

            is_end = self.room.on_rob(self)
            if is_end:
                self.change_state(State.PLAYING)
                logger.info('ROB END LANDLORD[%s]', self.room.landlord)

            response = [Pt.RSP_CALL_SCORE, {
                'uid': self.uid,
                'rob': self.rob,
                'landlord': self.room.landlord.uid if is_end else -1,
                'multiple': self.room.multiple,
                'pokers': self.room.pokers if is_end else [],
            }]
            self.room.broadcast(response)
        else:
            self.write_error('STATE[%s]' % self.state)

    @shot_turn
    def handle_playing(self, code, packet):
        if code == Pt.REQ_SHOT_POKER:
            pokers = packet.get('pokers')

            if not rule.is_contains(self._hand_pokers, pokers):
                self.write_error('Poker does not exist')
                return

            error = self.room.on_shot(self.seat, pokers)
            if error:
                self.write_error(error)
                return

            for p in pokers:
                self._hand_pokers.remove(p)

            self.room.broadcast([Pt.RSP_SHOT_POKER, {'uid': self.uid, 'pokers': pokers, 'multiple': self.room.multiple}])
            logger.info('USER[%d] shot %s', self.uid, pokers)

            if self._hand_pokers:
                self.room.go_next_turn()
            else:
                self.change_state(State.GAME_OVER)
                self.room.on_game_over(self)
        else:
            self.write_error('STATE[%s]' % self.state)

    def handle_game_over(self, code: int, packet: Dict[str, Any]):
        self.write_error('STATE[%s]' % self.state)

    def change_state(self, state: State):
        for player in self.room.players:
            player.state = state

    def write_message(self, packet):
        self.socket.write_message(packet)

    def write_error(self, reason: str):
        if self.socket:
            self.socket.write_message([Pt.ERROR, {'reason': reason}])
        logger.error('USER[%d][%s] %s', self.uid, self.state, reason)

    @property
    def ready(self) -> int:
        return self._ready

    @ready.setter
    def ready(self, val):
        self._ready = val
        if self.room:
            self.room.broadcast([Pt.RSP_READY, {'uid': self.uid, 'ready': self._ready}])

    def is_left(self) -> bool:
        return self._leave == 1

    @property
    def timeout(self):
        return 5 if self.is_left() else 20

    def set_left(self, is_left=1):
        self._leave = is_left
        if is_left:
            from .storage import Storage
            if self.room:
                self.room.broadcast([Pt.RSP_LEAVE_ROOM, {'uid': self.uid}])

    @property
    def allow_robot(self) -> bool:
        return self.socket.allow_robot

    def join_room(self, room: Room):
        if room.is_full():
            self.write_error('Room[%s] FULL' % room.room_id)
            return False

        self.set_left(0)
        self.room = room
        return room.on_join(self)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f'{self.uid}-{self.name}'

    def __eq__(self, other):
        return other and self.uid == other.uid

    def __ne__(self, other):
        return not (self == other)
