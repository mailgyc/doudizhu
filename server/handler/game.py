import functools
import logging

import tornado.escape
import tornado.ioloop
import tornado.web
import tornado.websocket
from bson import ObjectId

from handler.base import BaseSocketHandler
from model import rule
from model.table import Table

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def right_turn(method):
    @functools.wraps(method)
    def wrapper(handler, packet):
        if handler.player.seat == handler.player.table.whoseTurn:
            method(handler, packet)
        else:
            logger.warning('Player[%d] turn cheat', handler.uid)


@right_turn
def req_call_score(handler, packet):
    score = packet[1]
    if handler.player.table.callscore < score <= 3:
        handler.player.handle_call_score(score)
    else:
        logger.warning('Player[%d] callscore[%d] cheat', handler.uid, score)


@right_turn
def req_shot_poker(handler, packet):
    shot_poker = packet[1]
    if len(shot_poker) <= 0:
        logger.warning('Player[%d] play poker vicious', handler.uid)

    if not rule.containsAll(handler.player.pokers, shot_poker):
        logger.warning('Player[%d] play non-exist poker', handler.uid)
        return

    if handler.player.table.last_shot_seat != handler.player.seat and rule.compare(shot_poker,
                                                                                   handler.player.table.last_shot_poker) < 0:
        logger.warning('Player[%d] play less than poker', handler.uid)
        return

    handler.player.table.last_shot_poker = shot_poker
    handler.player.handle_shot_poker(shot_poker)

    for p in shot_poker:
        handler.player.pokers.remove(p)
    game_end = len(handler.player.pokers) == 0

    response = [106, handler.uid, shot_poker, game_end]
    message = tornado.escape.json_encode(response)
    for p in handler.player.table.players:
        p.send(message)

    if game_end:
        response = [108, handler.uid, handler.player.table.calc_coin(handler.player)]
        for p in handler.player.table.players:
            p.send(response)
    logger.info('Player[%d] shot_poker[%s]', handler.uid, ','.join(str(x) for x in shot_poker))


class GameHandler(BaseSocketHandler):

    def open(self):
        # GameHandler.sockets[self.uid] = self
        logger.info('socket[%s] open:', self.uid)

    def on_message(self, message):
        logger.info('on message: %s', message)
        packet = tornado.escape.json_decode(message)

        code = packet[0]
        if code == 1:
            self.req_player_info(packet)
        elif code == 11:
            self.req_table_list(packet)
        elif code == 13:
            self.req_join_table(packet)
        elif code == 15:
            self.req_fast_join_table(packet)
        elif code == 101:
            self.req_call_score(packet)
        elif code == 105:
            self.req_shot_poker(packet)
        elif code == 110:
            self.req_deal_poker(packet)
        else:
            logger.info('UNKNOWN PACKET: [%s]', code)

    def on_close(self):
        logger.info('socket[%s] close', self.uid)

        # if self.player.table and self.player.table.remove(self.player):
        #     logger.info('Table[%d] close', self.player.table.pid)
        #     SocketHandler.tableList.remove(self.player.table)

    def req_player_info(self, packet):
        response = [2, self.uid]
        self.write_message(tornado.escape.json_encode(response))

    def req_table_list(self, packet):
        response = [12, []]
        for t in self.redis.get('tables'):
            response[1].append(t.pid)
        self.write_message(tornado.escape.json_encode(response))

    def req_join_table(self, packet):
        table_id = packet[1]
        t = self.session.get(table_id)
        if not t:
            self.player.join_table(t)
            t = [self.uid, '', '', str(ObjectId())]
            logger.info('Player[%d] create Table[%d]', self.uid, self.player.seat, t[3])

        GameHandler.sync_table(t, 14)
        logger.info('Player[%d] join table[%d]', self.uid, t[3])

    def req_fast_join_table(self, packet):
        t = self.find_wait_table()
        self.player.join_table(t)

        GameHandler.sync_table(t, 16)
        logger.info('Player[%s] fast join table[%d]', self.uid, t.pid)

    def req_deal_poker(self, packet):
        if self.player.table.state == 2:
            self.player.ready = True
        self.player.table.ready()

    @staticmethod
    def sync_table(t, code):
        response = [code, t.pid, [p.pid if p else -1 for p in t.players]]
        for p in t.players:
            if p:
                p.send(response)
        if t.size() == 3:
            t.deal_poker()

    @classmethod
    def find_wait_table(cls):
        for t in cls.tableList:
            if t.size() < 3:
                return t
        t = Table()
        cls.tableList.append(t)
        return t

    @classmethod
    def send_updates(cls, chat):
        logger.info('sending message to %d waiters', len(cls.waiters))
        for waiter in cls.waiters:
            waiter.write_message('tornado:' + chat)
