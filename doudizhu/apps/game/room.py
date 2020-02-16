from __future__ import annotations

import logging
import random
from typing import Optional, List, Dict
from typing import TYPE_CHECKING

from tornado.ioloop import IOLoop

from .protocol import Protocol as Pt

if TYPE_CHECKING:
    from .player import Player


class Room(object):

    def __init__(self, room_id, entrance_fee=1, allow_robot=True):
        self.room_id = room_id
        self.entrance_fee = entrance_fee

        self.players: List[Optional[Player]] = [None, None, None]
        self.pokers: List[int] = []
        self.multiple = 1
        self.call_score = 0
        self.max_call_score = 0
        self.max_call_score_turn = 0
        self.whose_turn = 0
        self.last_shot_seat = 0
        self.last_shot_poker = []
        self.allow_robot = allow_robot
        logging.info('ROOM[%d] CREATED', room_id)

    def reset(self):
        self.pokers: List[int] = []
        self.multiple = 1
        self.call_score = 0
        self.max_call_score = 0
        self.max_call_score_turn = 0
        self.whose_turn = random.randint(0, 2)
        self.last_shot_seat = 0
        self.last_shot_poker = []

        for player in self.players:
            player.reset()

    def add_robot(self, nth=1):
        size = self.size()
        if size == 0 or size == 3:
            return

        if size == 2 and nth == 1:
            # only allow [human robot robot]
            return

        from .components.simple import RobotPlayer
        p1 = RobotPlayer(10 + nth, f'IDIOT-{nth}', self)
        p1.to_server([Pt.REQ_JOIN_ROOM, self.room_id, 0])

        if nth == 1:
            IOLoop.current().call_later(1, self.add_robot, nth=2)

    def arrange_seat(self, target: Player):
        for i, player in enumerate(self.players):
            if player:
                continue
            target.seat = i
            self.players[i] = target
            return True
        return False

    def on_join(self, target: Player):
        if self.arrange_seat(target):
            if self.allow_robot:
                IOLoop.current().call_later(0.1, self.add_robot, nth=1)
            return True
        return False

    def on_leave(self, target: Player):
        from .components.simple import RobotPlayer
        try:
            for i, player in enumerate(self.players):
                if player == target:
                    self.players[i] = None
                elif isinstance(player, RobotPlayer):
                    self.players[i] = None
            RoomManager.on_room_changed(self)
            return True
        except ValueError:
            logging.error('Player[%d] NOT IN Room[%d]', target.uid, self.room_id)
            return False

    def on_game_over(self, winner):
        point = self.entrance_fee * self.call_score * self.multiple

        response = [Pt.RSP_GAME_OVER, {
            'winner': winner.uid,
            'won_point': point,
            'lost_point': -point,
            'pokers': [],
        }]
        for target in self.players:
            response[1]['pokers'] = [[p.uid, *p.hand_pokers] for p in self.players if p != target]
            target.write_message(response)
        logging.info('Room[%d] GameOver[%d]', self.room_id, self.room_id)

    def deal_poker(self):
        self.pokers = [i for i in range(54)]
        random.shuffle(self.pokers)
        for i in range(51):
            self.players[i % 3].hand_pokers.append(self.pokers.pop())

        self.whose_turn = random.randint(0, 2)
        for player in self.players:
            player.hand_pokers.sort()

            response = [Pt.RSP_DEAL_POKER, self.turn_player.uid, player.hand_pokers]
            player.write_message(response)
            logging.info('ROOM[%s] DEAL[%s]', self.room_id, response)

    def call_score_end(self):
        self.call_score = self.max_call_score
        self.whose_turn = self.max_call_score_turn
        self.turn_player.role = 2
        self.turn_player.hand_pokers += self.pokers
        response = [Pt.RSP_SHOW_POKER, self.turn_player.uid, self.pokers]
        for p in self.players:
            p.write_message(response)
        logging.info('Player[%d] IS LANDLORD[%s]', self.turn_player.uid, str(self.pokers))

    def go_next_turn(self):
        self.whose_turn += 1
        if self.whose_turn == 3:
            self.whose_turn = 0

    @property
    def turn_player(self):
        return self.players[self.whose_turn]

    def handle_chat(self, player, msg):
        response = [Pt.RSP_CHAT, player.uid, msg]
        for p in self.players:
            p.write_message(response)

    def is_call_end(self):
        return all([p.is_called for p in self.players])

    def is_ready(self) -> bool:
        return self.is_full() and all([p.ready for p in self.players])

    def is_full(self) -> bool:
        return self.size() == 3

    def is_empty(self) -> bool:
        return self.size() == 0

    def size(self):
        return sum([p is not None for p in self.players])

    def __str__(self):
        return f'[{self.room_id}: {self.players}]'

    def __hash__(self):
        return self.room_id

    def __eq__(self, other):
        return self.room_id == other.room_id

    def __ne__(self, other):
        return not(self == other)


class RoomManager(object):
    __total_room_count = 0
    __waiting_rooms: Dict[int, Room] = {}
    __playing_rooms: Dict[int, Room] = {}

    @classmethod
    def new_room(cls, entrance_fee: int, allow_robot: bool) -> Room:
        room = Room(cls.gen_room_id(), entrance_fee, allow_robot)
        cls.__waiting_rooms[room.room_id] = room
        return room

    @classmethod
    def find_waiting_room(cls, uid: int, entrance_fee: int, allow_robot: bool) -> Room:
        if uid == -1:
            for _, room in cls.__waiting_rooms.items():
                return room
            return cls.new_room(entrance_fee, allow_robot)
        return cls.__waiting_rooms.get(uid)

    @classmethod
    def on_room_changed(cls, room: Room):
        if room.is_full():
            cls.__waiting_rooms.pop(room.room_id, None)
            cls.__playing_rooms[room.room_id] = room
            logging.info('Room[%d] full', room.room_id)
        if room.is_empty():
            cls.__playing_rooms.pop(room.room_id, None)
            cls.__waiting_rooms[room.room_id] = room
            logging.info('Room[%d] closed', room.room_id)

    @classmethod
    def get_waiting_rooms(cls) -> Dict[int, Room]:
        return cls.__waiting_rooms

    @classmethod
    def get_playing_rooms(cls) -> Dict[int, Room]:
        return cls.__playing_rooms

    @classmethod
    def gen_room_id(cls) -> int:
        cls.__total_room_count += 1
        return cls.__total_room_count
