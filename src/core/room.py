import logging

from core import Singleton
from core.table import Table

logger = logging.getLogger('ddz')


class Room(object):

    def __init__(self, uid, allow_robot=True):
        self.uid = uid
        self.__waiting_tables = {}
        self.__playing_tables = {}
        self.allow_robot = allow_robot
        self.entrance_fee = 100
        logger.info('ROOM[%d] CREATED', uid)

    def rsp_tables(self):
        rsp = []
        for _, t in self.waiting_tables.items():
            rsp.append([t.uid, t.size()])
        return rsp

    def new_table(self):
        t = Table(RoomManager.gen_table_id(), self)
        self.waiting_tables[t.uid] = t
        return t

    def find_waiting_table(self, uid, default=None):
        table = self.waiting_tables.get(uid, default)
        if table and table == default:
            self.waiting_tables[uid] = table
        return table

    def first_waiting_table(self):
        for _, table in self.waiting_tables.items():
            return table
        return self.new_table()

    def join_tables(self, tid):
        tables = self.waiting_tables
        for table in tables:
            if tid != table[0]:
                continue

            table.append(tid)
            if len(table) == 4:
                tables.remove(table)
            return True
        else:
            return False

    @property
    def waiting_tables(self):
        return self.__waiting_tables

    @property
    def playing_tables(self):
        return self.__playing_tables


class RoomManager(object):
    __metaclass__ = Singleton

    __room_dict = {
        1: Room(1, True),
        2: Room(2, False),
    }

    __current_table_id = 0

    @staticmethod
    def gen_table_id():
        RoomManager.__current_table_id += 1
        return RoomManager.__current_table_id

    @staticmethod
    def find_room(uid, created=False):
        room = RoomManager.__room_dict.get(uid)
        if not room and created:
            room = Room(uid)
            RoomManager.__room_dict[uid] = room
        return room
