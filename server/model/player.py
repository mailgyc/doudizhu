import tornado.escape

from model.table import logger


class Player(object):
    def __init__(self):
        self.socket = None
        self.table = None
        self.ready = False
        self.seat = 0
        self.is_called = False
        self.rank = 1  # landlord=2 farmer=1
        self.pokers = []

    def send(self, message):
        if not isinstance(message, str):
            message = tornado.escape.json_encode(message)
        self.socket.write_message(message)

    def deal_poker(self):
        player = self.table.players[self.table.whoseTurn]
        response = [100, player.pid, self.pokers]
        logger.info('Player[%d] deal_poker[%s]', self.pid, ','.join(str(x) for x in self.pokers))
        self.send(response)

    def handle_call_score(self, score):

        nextseat = (self.seat + 1) % 3
        callend = (score == 3 or self.table.players[nextseat].iscalled)

        response = [102, self.pid, score, callend]
        message = tornado.escape.json_encode(response)
        for p in self.table.players:
            p.send(message)

        logger.info('Player[%d] callscore[%d]', self.pid, score)
        if callend:
            if score == 0:
                self.table.deal_poker()
            else:
                self.rank = 2
                self.table.callscore = score
                response = [104, self.table.pokers]
                message = tornado.escape.json_encode(response)
                for p in self.table.players:
                    p.send(message)
                logger.info('Player[%d] is landlord[%s]', self.pid, ','.join(str(x) for x in self.table.pokers))
        else:
            self.table.whoseTurn = nextseat

    def join_table(self, t):
        t.add(self)
        self.ready = True
        self.table = t

