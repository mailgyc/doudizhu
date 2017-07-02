import functools
import json
import logging

import msgpack
from tornado.websocket import WebSocketHandler, WebSocketClosedError

from core.player import Player
from core.room import RoomManager, Room
from db import torndb
from .protocol import Protocol as Pt

logger = logging.getLogger('ddz')


def shot_turn(method):
    @functools.wraps(method)
    def wrapper(socket, packet):
        if socket.player.seat == socket.player.table.whose_turn:
            method(socket, packet)
        else:
            logger.warning('Player[%d] TURN CHEAT', socket.uid)
    return wrapper


class SocketHandler(WebSocketHandler):

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.db: torndb.Connection = self.application.db
        self.player: Player = None

    def data_received(self, chunk):
        logger.info('socket data_received')

    @property
    def uid(self):
        return self.player.uid

    @property
    def room(self):
        return self.player.room

    def open(self):
        self.player = Player(10, 'Jerry', self)
        self.player.room = RoomManager.find_room(0, True)
        logger.info('SOCKET[%s] OPEN', self.player.uid)

    def on_message(self, message):
        packet = msgpack.unpackb(message, use_list=False)
        # packet = json.loads(message)
        logger.info('REQ[%d]: %s', self.uid, packet)

        code = packet[0]
        if code == Pt.REQ_LOGIN:
            response = [Pt.RSP_LOGIN, self.player.uid, self.player.name]
            self.write_message(response)

        elif code == Pt.REQ_ROOM_LIST:
            response = [Pt.RSP_ROOM_LIST]
            self.write_message(response)

        elif code == Pt.REQ_TABLE_LIST:
            response = [Pt.RSP_TABLE_LIST, self.room.tables()]
            self.write_message(response)

        elif code == Pt.REQ_JOIN_TABLE:
            table_id = packet[1]
            table = self.find_table(table_id)
            if not table:
                response = [Pt.RSP_TABLE_LIST, self.room.tables()]
                self.write_message(response)
                logger.info('PLAYER[%d] JOIN FULL TABLE[%d]', self.uid, table.uid)

            self.player.join_table(table)
            logger.info('PLAYER[%s] JOIN TABLE[%d]', self.uid, table.uid)

            table.sync_table()
            if table.size() == 3:
                table.deal_poker()
                logger.info('TABLE[%s] GAME BEGIN[%s]', table.uid, table.players)
                del self.room.waiting_tables[table.uid]
                self.room.playing_tables[table.uid] = table

        elif code == Pt.REQ_CALL_SCORE:
            self.handle_call_score(packet)

        elif code == Pt.REQ_DEAL_POKER:
            if self.player.table.state == 2:
                self.player.ready = True
            self.player.table.ready()

        elif code == Pt.REQ_SHOT_POKER:
            self.handle_shot_poker(packet)
        else:
            logger.info('UNKNOWN PACKET: %s', code)

    @shot_turn
    def handle_call_score(self, packet):
        score = packet[1]
        self.player.handle_call_score(score)

    @shot_turn
    def handle_shot_poker(self, packet):
        pokers = packet[1]
        self.player.handle_shot_poker(pokers)

    def find_table(self, table_id):
        if table_id == -1:  # fast join
            return self.room.first_waiting_table()
        return self.room.find_waiting_table(table_id)

    def write_message(self, message, binary=False):
        if self.ws_connection is None:
            raise WebSocketClosedError()
        # packet = msgpack.packb(message)
        logger.info('RSP[%d]: %s', self.uid, message)
        packet = json.dumps(message)
        return self.ws_connection.write_message(packet, binary=binary)

    def on_close(self):
        # self.session.get(self.uid).socket = None
        logger.info('socket[%s] close', self.player.uid)
        # if self.player.table and self.player.table.remove(self.player):
        #     logger.info('Table[%d] close', self.player.table.pid)
        #     SocketHandler.tableList.remove(self.player.table)

    def send_updates(cls, chat):
        logger.info('sending message to %d waiters', len(cls.waiters))
        for waiter in cls.waiters:
            waiter.write_message('tornado:' + chat)


