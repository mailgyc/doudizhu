import logging

import functools
import tornado.escape
import tornado.ioloop
import tornado.web
import tornado.websocket
from bson import ObjectId

from base import BaseSocketHandler
from model.table import Table
from model import rule

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

sockets = {}


def req_player_info(handler, packet):
    response = [2, handler.uid]
    handler.write_message(tornado.escape.json_encode(response))


def req_table_list(handler, packet):
    response = [12, []]
    for t in handler.redis.get('tables'):
        response[1].append(t.pid)
    handler.write_message(tornado.escape.json_encode(response))


def req_join_table(handler, packet):
    table_id = packet[1]
    t = handler.session.get(table_id)
    if not t:
        handler.player.join_table(t)
        t = [handler.uid, '', '', str(ObjectId())]
        logger.info('Player[%d] create Table[%d]', handler.uid, handler.player.seat, t[3])

    handler.sync_table(t, 14)
    logger.info('Player[%d] join table[%d]', handler.uid, t[3])


def req_fast_join_table(handler, packet):
    t = SocketHandler.find_wait_table();
    handler.player.join_table(t)

    handler.sync_table(t, 16)
    logger.info('Player[%s] fast join table[%d]', handler.uid, t.pid)


def sync_table(t, opcode):
    response = [opcode, t.pid, [p.pid if p else -1 for p in t.players]]
    for p in t.players:
        if p:
            p.send(response)
    if t.size() == 3:
        t.deal_poker()


def right_turn(method):

    @functools.wraps(method)
    def wrapper(handler, packet):
        if handler.player.seat == handler.player.table.whoseTurn:
            method(handler, packet)
        else:
            logger.warning('Player[%d] turn cheat', handler.uid)


def req_deal_poker(handler, packet):
    if handler.player.table.state == 2:
        handler.player.ready = True
        handler.player.table.ready()


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

    if handler.player.table.last_shot_seat != handler.player.seat and rule.compare(shot_poker, handler.player.table.last_shot_poker) < 0:
        logger.warning('Player[%d] play less than poker', handler.uid)
        return

    handler.player.table.last_shot_poker = shot_poker
    handler.player.handle_shot_poker(shot_poker)

    for p in shot_poker:
        handler.player.pokers.remove(p)
    shotend = len(handler.player.pokers) == 0

    response = [106, handler.uid, shot_poker, shotend]
    message = tornado.escape.json_encode(response)
    for p in handler.player.table.players:
        p.send(message)

    if shotend:
        response = [108, handler.uid, handler.player.table.calc_coin(handler.player)]
        for p in handler.player.table.players:
            p.send(response)
    logger.info('Player[%d] shot_poker[%s]', handler.uid, ','.join(str(x) for x in shot_poker))


protocol_router = {
    1:  req_player_info,
    11: req_table_list,
    13: req_join_table,
    15: req_fast_join_table,
    101: req_call_score,
    105: req_shot_poker,
    110: req_deal_poker,
}


def handler_packet(handler, packet):
    func = protocol_router.get(packet[0])
    if func:
        func(handler, packet)
    else:
        logger.info('UNKNOWN PACKET: [%s]', packet[0])


class SocketHandler(BaseSocketHandler):

    tableList = []

    def initialize(self):
        pass

    def open(self):
        sockets[self.uid] = self
        logger.info('socket[%s] open:', self.uid)

    def on_message(self, message):
        logger.info('on message: %s', message)
        packet = tornado.escape.json_decode(message)
        handler_packet(self, packet)

    def on_close(self):
        logger.info('socket[%s] close', self.uid)

        # self.session
        # if self.player.table and self.player.table.remove(self.player):
        #     logger.info('Table[%d] close', self.player.table.pid)
        #     SocketHandler.tableList.remove(self.player.table)

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
