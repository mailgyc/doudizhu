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
        self.pid = next(Player.gen_id())
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
        if request[0] == 101: # request deal poker
            self.ready = True
            self.table.ready()
            return
            
        if self.seat != self.table.whoseTurn:
            return
            
        if request[0] == 103: # request call score
            score = request[1]
            if score > 0 and score < self.table.callscore:
                logger.warning('Player[%d] callscore cheat', self.pid)
                return
            response = [104, self.pid, score]
            message = tornado.escape.json_encode(packet)
            for p in self.table.players:
                p.send(message)
            
            nextseat = (self.seat + 1) % 3
            if score < 3 and not self.table.players[nextseat].iscalled:
                self.table.whoseTurn = nextseat
                return 
            
            if score == 0:
                self.table.ready()
            else:
                self.rank = 2
                self.table.callscore = score 
                response = [106, self.pid, [p for p in self.table.pokers]]
                message = tornado.escape.json_encode(response)
                for p in self.table.players:
                    p.send(message)
            
        elif request[0] == 107: # request play poker
            shotPoker = request[1]
            if len(shotPoker) > 0:
                if not rule.containsAll(self.poker, shotPoker):
                    logger.warning('Player[%d] play non-exist poker', self.pid) 
                    return
               
                if self.table.lastShotSeat != self.seat and rule.compare(shotPoker, self.table.lastShotPoker) < 0:
                    logger.warning('Player[%d] play less than poker', self.pid) 
                    return
                    
                self.table.lastShotPoker = shotPoker
            
            response = [108, self.pid, shotPoker]
            message = tornado.escape.json_encode(packet)
            for p in self.table.players:
                p.send(message)
            for p in shotPoker:
                self.pokers.remove(p)
                
            if len(self.pokers) == 0:
                response = [110, self.table.calcCoin(self)]
                for p in self.table.players:
                    p.send(response) 
            
            
    def dealPoker(self):
        response = [102, self.table.whoseTurn, []]
        for p in self.pokers:
            response[1].append(p)
        logger.info('Player[%d] dealPoker[%s]', self.pid, ','.join(response[1]))
        self.send(response)
         
    def join_table(self, t):
        t.add(self)
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
        self.closed = False
        self.pokers = [] 
        self.multiple = 1
        self.callscore = 0
        self.whoseTurn = 0
        self.lastShotSeat = 0;
        self.lastShotPoker = [];
        self.room = 100
        tornado.ioloop.IOLoop.current().add_callback(self.update)

    def calcCoin(self, winner):
        coins = []
        recycle = 100 
        for p in self.players:
            p.ready = f
            coin = self.room * p.rank * self.callscore * self.multiple
            if p.rank == winner.rank:
                coins.append(coin - recycle)
            else:
                coins.append(-coin - recycle)
        return coins     
        
    def update(self):
        logger.info('table[%d] update', self.pid)

    def add(self, player):
        for i, p in enumerate(self.players):
            if not p:
                player.seat = i
                self.players[i] = player
                return True
        logger.error('Player[%d] join a full Table[%d]', player.pid, self.pid)
        return False

    def remove(self, player):
        for i, p in enumerate(self.players):
            if p.pid == player.pid:
                self.players[i] = None
        else:
            logger.error('Player[%d] not in Table[%d]', player.pid, self.pid)
            
        if all(p == None for p in self.players):
            self.closed = True
            logger.error('Table[%d] close', self.pid)
            return True
        return False

    def size(self):
        return 3 - self.players.count(None)
    
    def ready(self):
        if all(p and p.ready for p in self.players):
            self.dealPoker()

    def dealPoker(self):
        self.pokers = [0 for i in range(54)]
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




