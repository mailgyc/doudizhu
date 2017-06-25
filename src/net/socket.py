import functools
import json
import logging

import msgpack
from tornado.websocket import WebSocketHandler, WebSocketClosedError

from core.player import Player
from core.table import Table
from db import torndb
from .protocol import Protocol as Pt

logger = logging.getLogger('ddz')


def shot_turn(method):
    @functools.wraps(method)
    def wrapper(handler, packet):
        if handler.player.seat == handler.player.table.whose_turn:
            method(handler, packet)
        else:
            logger.warning('Player[%d] turn cheat', handler.uid)


waiting_tables = {}
playing_tables = {}


class SocketHandler(WebSocketHandler):

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.db: torndb.Connection = self.application.db
        self.player = None

    def data_received(self, chunk):
        logger.info('socket data_received')

    @property
    def uid(self):
        self.player.uid

    def open(self):
        self.player = Player(10, 'Jerry', self)
        logger.info('socket[%s] open', self.player.uid)

    def on_message(self, message):
        packet = msgpack.unpackb(message, use_list=False)
        # packet = json.loads(message)
        logger.info('on message: %s', packet)

        code = packet[0]
        if code == Pt.REQ_LOGIN:
            response = [Pt.RSP_LOGIN, self.player.uid, self.player.name]
            self.write_message(response)

        elif code == Pt.REQ_ROOM_LIST:
            response = [Pt.RSP_ROOM_LIST]
            self.write_message(response)

        elif code == Pt.REQ_TABLE_LIST:
            response = [Pt.RSP_TABLE_LIST, waiting_tables.keys() + playing_tables.keys()]
            self.write_message(response)

        elif code == Pt.REQ_JOIN_TABLE:
            table_id = packet[1]
            table = self.find_table(table_id)
            if not table:
                response = [Pt.RSP_TABLE_LIST, waiting_tables.keys() + playing_tables.keys()]
                self.write_message(response)
                logger.info('PLAYER[%d] JOIN FULL TABLE[%d]', self.uid, table.uid)

            self.player.join_table(table)
            table.sync_table()
            if table.size() == 3:
                del waiting_tables[table.uid]
                playing_tables[table.uid] = table
            logger.info('PLAYER[%s] JOIN TABLE[%d]', self.uid, table.uid)

        elif code == Pt.REQ_CALL_SCORE:
            score = packet[1]
            if self.player.table.call_score < score <= 3:
                self.player.handle_call_score(score)
            else:
                logger.warning('Player[%d] call score[%d] cheat', self.uid, score)

        elif code == Pt.REQ_DEAL_POKER:
            if self.player.table.state == 2:
                self.player.ready = True
            self.player.table.ready()

        elif code == Pt.REQ_SHOT_POKER:
            self.shot_poker(packet)
        elif code == Pt.REQ_NO_SHOT:
            self.no_shot(packet)
        else:
            logger.info('UNKNOWN PACKET: %s', code)

    @staticmethod
    def find_table(table_id):
        if table_id == -1:  # fast join
            if not waiting_tables:
                table = Table()
                waiting_tables[table.uid] = table
                return table

        for _, table in waiting_tables.items():
            return table

        return waiting_tables.get(table_id, None)

    def write_message(self, message, binary=False):
        if self.ws_connection is None:
            raise WebSocketClosedError()
        # packet = msgpack.packb(message)
        packet = json.dumps(message)
        return self.ws_connection.write_message(packet, binary=binary)

    def on_close(self):
        # self.session.get(self.uid).socket = None
        logger.info('socket[%s] close', self.player.uid)
        # if self.player.table and self.player.table.remove(self.player):
        #     logger.info('Table[%d] close', self.player.table.pid)
        #     SocketHandler.tableList.remove(self.player.table)

    @shot_turn
    def shot_poker(self, packet):
        pokers = packet[1]
        if len(pokers) <= 0:
            logger.warning('Player[%d] play poker vicious', self.uid)

        self.player.shot_poker(pokers)

    @shot_turn
    def no_poker(self, packet):
        self.player.no_shot()

    @classmethod
    def send_updates(cls, chat):
        logger.info('sending message to %d waiters', len(cls.waiters))
        for waiter in cls.waiters:
            waiter.write_message('tornado:' + chat)


