from __future__ import annotations

import functools
import logging
from enum import IntEnum, auto
from typing import TYPE_CHECKING, List, Optional, Union, Any

from .protocol import Protocol as Pt
from .room import RoomManager
from .rule import rule

if TYPE_CHECKING:
    from .room import Room
    from .views import SocketHandler

logger = logging.getLogger(__file__)

FARMER = 1
LANDLORD = 2


def shot_turn(method):
    @functools.wraps(method)
    def wrapper(player, packet):
        if player.seat == player.room.whose_turn:
            method(player, packet)
        else:
            logging.warning('USER[%d] TURN CHEAT', player.uid)

    return wrapper


class State(IntEnum):
    INIT = auto()
    WAITING = auto()
    CALL_SCORE = auto()
    PLAYING = auto()
    GAME_OVER = auto()
    DISCONNECT = auto()


class Player(object):

    def __init__(self, uid: int, name: str, socket: SocketHandler = None):
        self.uid = uid
        self.name = name
        self.socket = socket
        self.room: Optional[Room] = None
        self.seat = 0
        self.state = State.INIT

        self.ready = False
        self.role = FARMER
        self.rob = -1
        self._hand_pokers: List[int] = []

    def reset(self):
        self.ready = False
        self.role = FARMER
        self.rob = -1
        self._hand_pokers: List[int] = []

    def on_message(self, packet):
        if self.state == State.INIT:
            self.handle_init(packet)
        elif self.state == State.WAITING:
            self.handle_waiting(packet)
        elif self.state == State.CALL_SCORE:
            self.handle_call_score(packet)
        elif self.state == State.PLAYING:
            self.handle_playing(packet)
        elif self.state == State.GAME_OVER:
            self.handle_game_over(packet)
        elif self.state == State.DISCONNECT:
            pass

    def handle_init(self, packet):
        code = packet[0]
        if code == Pt.REQ_LOGIN:
            response = [Pt.RSP_LOGIN, self.uid, self.name]
            self.write_message(response)

        elif code == Pt.REQ_ROOM_LIST:
            self.write_message([Pt.RSP_ROOM_LIST, RoomManager.get_waiting_rooms()])

        elif code == Pt.REQ_NEW_ROOM:
            # TODO: check target was already in a room.
            entrance_fee = packet[1]
            room = RoomManager.new_room(entrance_fee, self.allow_robot)
            if self.join_room(room):
                self.sync_room()
            logging.info('PLAYER[%s] NEW ROOM[%d]', self.uid, room.room_id)
            self.write_message([Pt.RSP_NEW_ROOM, room.room_id])

        elif code == Pt.REQ_JOIN_ROOM:
            room_id, entrance_fee = packet[1], packet[2]
            room = RoomManager.find_waiting_room(room_id, entrance_fee, self.allow_robot)
            if not room:
                self.write_message([Pt.RSP_ERROR, 'ROOM NOT FOUND'])
                logging.info('PLAYER[%d] JOIN ROOM[%d] NOT FOUND', self.uid, packet[1])
                return

            self.state = State.WAITING
            if self.join_room(room):
                self.sync_room()
            logging.info('PLAYER[%s] JOIN ROOM[%d]', self.uid, room.room_id)

            if room.is_full():
                RoomManager.on_room_changed(room)
                logging.info('ROOM[%s] FULL[%s]', room.room_id, room.players)
        else:
            logging.info('ERROR STATE[%s] PACKET %s', self.state, packet)

    def handle_waiting(self, packet):
        code = packet[0]
        if code == Pt.REQ_READY:
            self.ready = True
            self.write_message([Pt.RSP_READY])
            if self.room.is_ready():
                self.change_state(State.CALL_SCORE)
                self.room.deal_poker()
        else:
            logging.info('ERROR STATE[%s] PACKET %s', self.state, packet)

    @shot_turn
    def handle_call_score(self, packet):
        code = packet[0]
        if code == Pt.REQ_CALL_SCORE:
            self.rob = packet[1]

            call_end = self.room.is_rob_end()
            response = [Pt.RSP_CALL_SCORE, self.uid, self.rob, call_end]
            for p in self.room.players:
                p.write_message(response)

            if call_end:
                self.change_state(State.PLAYING)
                self.room.sync_call_end()

        else:
            logging.info('ERROR STATE[%s] PACKET %s', self.state, packet)

    @shot_turn
    def handle_playing(self, packet):
        code = packet[0]
        if code == Pt.REQ_SHOT_POKER:
            pokers = packet[1]
            if pokers:
                if not rule.is_contains(self._hand_pokers, pokers):
                    logger.warning('USER[%d] play non-exist poker', self.uid)
                    return

                if self.room.last_shot_seat != self.seat and rule.compare_poker(pokers, self.room.last_shot_poker) < 0:
                    logger.warning('USER[%d] play small than last shot poker', self.uid)
                    return

                self.room.last_shot_seat = self.seat
                self.room.last_shot_poker = pokers
                for p in pokers:
                    self._hand_pokers.remove(p)

            response = [Pt.RSP_SHOT_POKER, self.uid, pokers]
            for p in self.room.players:
                p.write_message(response)
            logger.info('USER[%d] shot[%s]', self.uid, str(pokers))

            if self._hand_pokers:
                self.room.go_next_turn()
            else:
                self.change_state(State.GAME_OVER)
                self.room.on_game_over(self)

        elif code == Pt.REQ_CHEAT:
            self.on_cheat(packet[1])
        else:
            logging.info('ERROR STATE[%s] PACKET %s', self.state, packet)

    def handle_game_over(self, packet):
        code = packet[0]
        if code == Pt.REQ_RESTART:
            self.state = State.WAITING
        else:
            logging.info('ERROR STATE[%s] PACKET %s', self.state, packet)

    def change_state(self, state: State):
        for player in self.room.players:
            player.state = state

    def on_cheat(self, uid):
        for p in self.room.players:
            if p.uid == uid:
                self.write_message([Pt.RSP_CHEAT, p.uid, p._hand_pokers])

    def write_message(self, packet):
        self.socket.write_message(packet)

    @property
    def allow_robot(self) -> bool:
        return self.socket.allow_robot

    def sync_room(self):
        response = [Pt.RSP_JOIN_ROOM, {
            'room': self.room.sync_data(),
            'players': [p.sync_data() if p else {} for p in self.room.players]
        }]
        for player in self.room.players:
            if player:
                player.write_message(response)

    def sync_data(self):
        return {
            'uid': self.uid,
            'name': self.name,
            'icon': '',
            'ready': self.ready,
        }

    def join_room(self, room: Room):
        if room.is_full():
            logging.error('USER[%d] Join Room[%d] FULL', self.uid, room.room_id)
            return False

        self.room = room
        return room.on_join(self)

    def leave_room(self):
        self.ready = False
        if self.room:
            self.room.on_leave(self)
        self.room = None

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f'{self.uid}-{self.name}'
