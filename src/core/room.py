import logging

from core import Singleton
from core.table import Table

logger = logging.getLogger('ddz')


class Room(object):

    def __init__(self, uid):
        self.uid = uid
        self.__waiting_tables = {}
        self.__playing_tables = {}
        logger.info('ROOM[%d] CREATED', uid)

    def find_waiting_table(self, uid, default=None):
        table = self.waiting_tables.get(uid, default)
        if table and table == default:
            self.waiting_tables[uid] = table
        return table

    def first_waiting_table(self):
        for _, table in self.waiting_tables.items():
            return table
        t = Table()
        self.waiting_tables[t.uid] = t
        return t

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
    def tables(self):
        l = []
        l.extend(self.waiting_tables.keys())
        l.extend(self.playing_tables.keys())
        return l

    @property
    def waiting_tables(self):
        return self.__waiting_tables

    @property
    def playing_tables(self):
        return self.__playing_tables


class RoomManager(object):
    __metaclass__ = Singleton

    __room_dict = {}

    @staticmethod
    def find_room(uid, created=False):
        room = RoomManager.__room_dict.get(uid)
        if not room and created:
            room = Room(0)
            RoomManager.__room_dict[uid] = room
        return room
