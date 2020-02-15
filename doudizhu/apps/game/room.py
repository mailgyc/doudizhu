import logging
import random
from typing import Optional, List, Dict

from tornado.ioloop import IOLoop

from .components.simple import AiPlayer
from .player import Player
from .protocol import Protocol as Pt


class Room(object):
    WAITING = 0
    PLAYING = 1
    END = 2
    CLOSED = 3

    def __init__(self, room_id, entrance_fee=1, allow_robot=True):
        self.room_id = room_id
        self.entrance_fee = entrance_fee

        self.players: List[Optional[Player]] = [None, None, None]
        self.state = 0  # 0 waiting  1 playing 2 end 3 closed
        self.pokers: List[int] = []
        self.multiple = 1
        self.call_score = 0
        self.max_call_score = 0
        self.max_call_score_turn = 0
        self.whose_turn = 0
        self.last_shot_seat = 0
        self.last_shot_poker = []
        self.history = [None, None, None]
        if allow_robot:
            IOLoop.current().call_later(0.1, self.add_robot, nth=1)
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
        if self.is_full():
            self.deal_poker()
            RoomManager.on_room_changed(self)
            logging.info('ROOM[%s] GAME BEGIN[%s]', self.room_id, self.players[0].uid)

    def add_robot(self, nth=1):
        size = self.size()
        if size == 0 or size == 3:
            return

        if size == 2 and nth == 1:
            # only allow [human robot robot]
            return

        p1 = AiPlayer(10 + nth, f'IDIOT-{nth}', self)
        p1.to_server([Pt.REQ_JOIN_ROOM, self.room_id, 0])

        if nth == 1:
            IOLoop.current().call_later(1, self.add_robot, nth=2)

    def arrange_seat(self, player: Player):
        if self.is_full():
            logging.error('Player[%d] JOIN Room[%d] FULL', player.uid, self.room_id)

        # arrange seat
        for i, p in enumerate(self.players):
            if not p:
                player.seat = i
                self.players[i] = player
                self.history[i] = []
                break
        self.sync_room()

    def on_leave(self, player: Player):
        for i, p in enumerate(self.players):
            if p == player:
                self.players[i] = None
                self.history[i] = None
                break

    def on_game_over(self, winner):
        # if winner.hand_pokers:
        #     return
        coin = self.entrance_fee * self.call_score * self.multiple
        for p in self.players:
            response = [Pt.RSP_GAME_OVER, winner.uid, coin if p != winner else coin * 2 - 100]
            for pp in self.players:
                if pp != p:
                    response.append([pp.uid, *pp.hand_pokers])
            p.send(response)
        # TODO deduct coin from database
        # TODO store poker round to database
        logging.info('Room[%d] GameOver[%d]', self.room_id, self.room_id)

    def sync_room(self):
        ps = []
        for p in self.players:
            if p:
                ps.append((p.uid, p.name))
            else:
                ps.append((-1, ''))
        response = [Pt.RSP_JOIN_ROOM, self.room_id, ps]
        for player in self.players:
            if player:
                player.send(response)

    def deal_poker(self):
        if not all(p and p.ready for p in self.players):
            return

        self.state = Room.PLAYING
        self.pokers = [i for i in range(54)]
        random.shuffle(self.pokers)
        for i in range(51):
            self.players[i % 3].hand_pokers.append(self.pokers.pop())

        self.whose_turn = random.randint(0, 2)
        for p in self.players:
            p.hand_pokers.sort()

            response = [Pt.RSP_DEAL_POKER, self.turn_player.uid, p.hand_pokers]
            p.send(response)

    def call_score_end(self):
        self.call_score = self.max_call_score
        self.whose_turn = self.max_call_score_turn
        self.turn_player.role = 2
        self.turn_player.hand_pokers += self.pokers
        response = [Pt.RSP_SHOW_POKER, self.turn_player.uid, self.pokers]
        for p in self.players:
            p.send(response)
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
            p.send(response)

    def remove(self, player):
        for i, p in enumerate(self.players):
            if p and p.uid == player.uid:
                self.players[i] = None
                self.history[i] = None
        else:
            logging.error('Player[%d] NOT IN Room[%d]', player.uid, self.room_id)

        if all(p is None for p in self.players):
            self.state = 3
            logging.error('Room[%d] close', self.room_id)
            return True
        return False

    def all_called(self):
        for p in self.players:
            if not p.is_called:
                return False
        return True

    def is_full(self):
        return self.size() == 3

    def is_empty(self):
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
        if room.is_empty():
            cls.__playing_rooms.pop(room.room_id, None)
            cls.__waiting_rooms[room.room_id] = room

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
