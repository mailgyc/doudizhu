class Room(object):
    def __init__(self):
        self.waiting_tables = {}
        self.playing_tables = {}
        self.players = []

    @property
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

    @staticmethod
    def get(self, tid):
        self.session.pubsub(tid)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class RoomManager(object):
    __metaclass__ = Singleton

    room_dict = {}

    @staticmethod
    def get_room(uid, default=None):
        return RoomManager.room_dict.get(uid, default)
