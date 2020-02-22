from __future__ import annotations

import functools
import logging
from enum import IntEnum
from typing import TYPE_CHECKING, List, Optional, Dict, Any

from .protocol import Protocol as Pt
from .rule import rule

if TYPE_CHECKING:
    from .room import Room

logger = logging.getLogger(__file__)


def shot_turn(method):
    @functools.wraps(method)
    def wrapper(player, *args, **kwargs):
        if player.room and player.room.whose_turn == player.seat:
            method(player, *args, **kwargs)
        else:
            player.write_error('NOT YOUR TURN')

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
        self.room: Optional[Room] = None
        self.seat = -1
        self.state = State.INIT

        self._ready = 0
        self._leave = 0

        self.rob = -1
        self.landlord = 0
        self._hand_pokers: List[int] = []

        self.socket = None

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
            'icon': '',
            'ready': self.ready,
            'rob': self.rob,
            'leave': self.leave,
            'landlord': self.landlord,
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

    def on_message(self, message):
        if len(message) < 2 or not (isinstance(message[0], int) and isinstance(message[1], dict)):
            self.write_error('Protocol cannot be resolved.')
            return

        code, packet = message[0], message[1]
        if self.leave == 1:
            if self.handle_leave(code, packet):
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
        if self.state == State.INIT:
            self.leave_room()
        elif self.state == State.WAITING:
            self.leave_room()
        elif self.state == State.CALL_SCORE or self.state == State.PLAYING:
            self.leave = 1
        elif self.state == State.GAME_OVER:
            self.leave_room()

    def handle_leave(self, code: int, packet: Dict[str, Any]):
        from .storage import Storage
        if code == Pt.REQ_JOIN_ROOM:
            room_id, level = packet.get('room', -1), packet.get('level', 1)
            if room_id == -1:
                self.leave_room()
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

        if code == Pt.REQ_ROOM_LIST:
            pass

        elif code == Pt.REQ_NEW_ROOM:
            pass

        elif code == Pt.REQ_JOIN_ROOM:
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
            logger.info('ERROR STATE[%s] PACKET %s', self.state, packet)

    def handle_waiting(self, code: int, packet: Dict[str, Any]):
        if code == Pt.REQ_READY:
            self.ready = packet.get('ready')
            if self.room.is_ready():
                self.change_state(State.CALL_SCORE)
                self.room.deal_poker()
        elif code == Pt.REQ_LEAVE_ROOM:
            self.leave_room()
        else:
            self.write_error('STATE[%s]' % self.state)

    @shot_turn
    def handle_call_score(self, code: int, packet: Dict[str, Any]):
        if code == Pt.REQ_CALL_SCORE:
            self.rob = packet.get('rob')

            is_end = self.room.is_rob_end()
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
        elif code == Pt.REQ_LEAVE_ROOM:
            self.leave = 1

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
        elif code == Pt.REQ_LEAVE_ROOM:
            self.leave = 1
        else:
            self.write_error('STATE[%s]' % self.state)

    def handle_game_over(self, code: int, packet: Dict[str, Any]):
        self.write_error('STATE[%s]' % self.state)

    def change_state(self, state: State):
        for player in self.room.players:
            player.state = state

    def write_message(self, packet: List[int, Dict[str, Any]]):
        self.socket.write_message(packet)

    def write_error(self, reason: str):
        if self.socket:
            self.socket.write_message([Pt.ERROR, {'reason': reason}])
        logger.error('USER[%d] %s', self.uid, reason)

    @property
    def ready(self) -> int:
        return self._ready

    @ready.setter
    def ready(self, r):
        self._ready = r
        if self.room:
            self.room.broadcast([Pt.RSP_READY, {'uid': self.uid, 'ready': r}])

    @property
    def leave(self) -> int:
        return self._leave

    @leave.setter
    def leave(self, r: int):
        self._leave = r
        if self.room:
            self.room.broadcast([Pt.RSP_LEAVE_ROOM, {'uid': self.uid}])

    @property
    def allow_robot(self) -> bool:
        return self.socket.allow_robot

    def join_room(self, room: Room):
        if room.is_full():
            self.write_error('Room[%s] FULL' % room.room_id)
            return False

        self.leave = 0
        self.room = room
        return room.on_join(self)

    def leave_room(self):
        from .storage import Storage
        self.ready = 0
        if self.room:
            self.room.on_leave(self)
            self.leave = 1
            self.room = None
        Storage.remove_player(self.uid)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f'{self.uid}-{self.name}'

    def __eq__(self, other):
        return self.uid == other.uid

    def __ne__(self, other):
        return not (self == other)