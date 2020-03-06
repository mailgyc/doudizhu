import logging
from typing import Dict

from .player import Player
from .room import Room


class Storage(object):
    total_room_count = 0
    __players__: Dict[int, Player] = {}
    __waiting_rooms__: Dict[int, Room] = {}
    __playing_rooms__: Dict[int, Room] = {}

    @classmethod
    def room_list(cls):
        rooms = {1: 33, 2: 0, 3: 0}
        for room in cls.__playing_rooms__.values():
            if room.level in rooms:
                rooms[room.level] += 3
            else:
                rooms[room.level] = 0
        return [{'level': k, 'number': v} for k, v in rooms.items()]

    @classmethod
    def find_or_create_player(cls, uid: int, *args, **kwargs) -> Player:
        if uid not in cls.__players__:
            cls.__players__[uid] = Player(uid, *args, **kwargs)
        return cls.__players__[uid]

    @classmethod
    def find_player_room_id(cls, uid: int) -> int:
        player = cls.__players__.get(uid)
        if player and player.room:
            return player.room.room_id
        return -1

    @classmethod
    def remove_player(cls, uid: int):
        cls.__players__.pop(uid, None)

    @classmethod
    def new_room(cls, level: int, allow_robot: bool) -> Room:
        room = Room(cls.gen_room_id(), level, allow_robot)
        cls.__waiting_rooms__[room.room_id] = room
        logging.info('ROOM[%s] CREATED', room)
        return room

    @classmethod
    def find_room(cls, room_id: int, level: int, allow_robot: bool) -> Room:
        if room_id in cls.__waiting_rooms__:
            return cls.__waiting_rooms__[room_id]

        if room_id in cls.__playing_rooms__:
            return cls.__playing_rooms__[room_id]

        for _, room in cls.__waiting_rooms__.items():
            if room.level != level or room.has_robot():
                continue
            return room
        return cls.new_room(level, allow_robot)

    @classmethod
    def on_room_changed(cls, room: Room):
        if room.is_full():
            cls.__waiting_rooms__.pop(room.room_id, None)
            cls.__playing_rooms__[room.room_id] = room
            logging.info('Room[%s] FULL', room)
        if room.is_empty():
            cls.__waiting_rooms__.pop(room.room_id, None)
            cls.__playing_rooms__.pop(room.room_id, None)
            logging.info('Room[%s] CLOSED', room)

    @classmethod
    def gen_room_id(cls) -> int:
        cls.total_room_count += 1
        if cls.total_room_count > 999999:
            cls.total_room_count = 1
        return cls.total_room_count
