import logging
import uuid
import random
import tornado.escape
import tornado.ioloop
import tornado.websocket
import rule

logger = logging.getLogger()

class Player(object):

    def __init__(self):
        self.pid = Player.gen_id()
        self.socket = None
        self.table = None
        self.ready = False
        self.seat = 0
        self.iscalled = False
        self.rank = 1  # landlord=2 farmer=1
        self.pokers = []

    def send(self, message):
        if not isinstance(message, str):
            message = tornado.escape.json_encode(message)
        self.socket.write_message(message)

    def recv(self, request):
        if request[0] == 110: # request deal poker
            if self.table.state == 2:
                self.ready = True
                self.table.ready()
            return

        if self.seat != self.table.whoseTurn:
            logger.warning('Player[%d] turn cheat', self.pid)
            return

        if request[0] == 101: # request call score
            score = request[1]
            if score > 3 or (score > 0 and score < self.table.callscore):
                logger.warning('Player[%d] callscore[%d] cheat', self.pid, score)
                return
            self.handleCallScore(score)
        elif request[0] == 105: # request shot poker
            shotPoker = request[1]
            if len(shotPoker) > 0:
                if not rule.containsAll(self.pokers, shotPoker):
                    logger.warning('Player[%d] play non-exist poker', self.pid)
                    return

                if self.table.lastShotSeat != self.seat and rule.compare(shotPoker, self.table.lastShotPoker) < 0:
                    logger.warning('Player[%d] play less than poker', self.pid)
                    return

                self.table.lastShotPoker = shotPoker

            self.handleShotPoker(shotPoker)


    def dealPoker(self):
        player = self.table.players[self.table.whoseTurn]
        response = [100, player.pid, self.pokers]
        logger.info('Player[%d] dealPoker[%s]', self.pid, ','.join(str(x) for x in self.pokers))
        self.send(response)

    def handleCallScore(self, score):

        nextseat = (self.seat + 1) % 3
        callend = (score == 3 or self.table.players[nextseat].iscalled)

        response = [102, self.pid, score, callend]
        message = tornado.escape.json_encode(response)
        for p in self.table.players:
            p.send(message)

        logger.info('Player[%d] callscore[%d]', self.pid, score)
        if callend:
            if score == 0:
                self.table.dealPoker()
            else:
                self.rank = 2
                self.table.callscore = score
                self.pokers = self.pokers + self.table.pokers
                response = [104, self.table.pokers]
                message = tornado.escape.json_encode(response)
                for p in self.table.players:
                    p.send(message)
                logger.info('Player[%d] is landlord[%s]', self.pid, ','.join(str(x) for x in self.table.pokers))
        else:
            self.table.whoseTurn = nextseat


    def handleShotPoker(self, shotPoker):
        logger.info('Player[%d] shotPoker[%s]', self.pid, ','.join(str(x) for x in shotPoker))
        for p in shotPoker:
            self.pokers.remove(p)
        shotend = len(self.pokers) == 0

        response = [106, self.pid, shotPoker, shotend]
        message = tornado.escape.json_encode(response)
        for p in self.table.players:
            p.send(message)

        if shotend:
            response = [108, self.pid, self.table.calcCoin(self)]
            for p in self.table.players:
                p.send(response)

    def join_table(self, t):
        t.add(self)
        self.ready = True
        self.table = t

    def open(self, socket):
        self.socket = socket

    counter = 1000
    @classmethod
    def gen_id(cls):
        cls.counter +=1
        return cls.counter

class Table(object):

    def __init__(self):
        self.pid = Table.gen_id()
        self.players = [None, None, None]
        self.state = 0  # 0 waiting  1 playing 2 end 3 closed
        self.pokers = []
        self.multiple = 1
        self.callscore = 0
        self.whoseTurn = 0
        self.lastShotSeat = 0;
        self.lastShotPoker = [];
        self.room = 100
        tornado.ioloop.IOLoop.current().add_callback(self.update)

    def calcCoin(self, winner):
        self.state = 2
        coins = []
        tax = 100
        for p in self.players:
            p.ready = f
            coin = self.room * p.rank * self.callscore * self.multiple
            if p.rank == winner.rank:
                coins.append(coin - tax)
            else:
                coins.append(-coin - tax)
        return coins

    def update(self):
        logger.info('table[%d] update', self.pid)

    def add(self, player):
        for i, p in enumerate(self.players):
            if not p:
                player.seat = i
                self.players[i] = player
                logger.info('Table[%d] add Player[%d]', self.pid, player.pid)
                return True
        logger.error('Player[%d] join a full Table[%d]', player.pid, self.pid)
        return False

    def remove(self, player):
        for i, p in enumerate(self.players):
            if p and p.pid == player.pid:
                self.players[i] = None
        else:
            logger.error('Player[%d] not in Table[%d]', player.pid, self.pid)

        if all(p == None for p in self.players):
            self.state = 3
            logger.error('Table[%d] close', self.pid)
            return True
        return False

    def size(self):
        return 3 - self.players.count(None)

    def dealPoker(self):
        if not all(p and p.ready for p in self.players):
            return

        self.state = 1
        self.pokers = [i for i in range(54)]
        random.shuffle(self.pokers)
        for i in range(51):
            self.players[i % 3].pokers.append(self.pokers.pop())

        self.whoseTurn = random.randint(0, 2)
        for p in self.players:
            p.dealPoker()

    counter = 0
    @classmethod
    def gen_id(cls):
        cls.counter += 1
        return cls.counter

if __name__ == '__main__':
    t = Table()
    print(t.pid)
    t = Table()
    print(t.pid)
    t = Table()
    print(t.pid)
    t = Table()
    print(t.pid)




