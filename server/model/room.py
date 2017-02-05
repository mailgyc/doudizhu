
class Room(object):

    def __init__(self):
        self.waiting_tables = []
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

    def on_leave(self, tid):
        self.session.pubsub(tid)