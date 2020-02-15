import functools
import json
import logging
from typing import Optional, List, Union, Any

from tornado.escape import json_decode
from tornado.ioloop import IOLoop
from tornado.web import authenticated
from tornado.websocket import WebSocketHandler, WebSocketClosedError

from contrib.db import AsyncConnection
from contrib.handlers import RestfulHandler
from .player import Player
from .protocol import Protocol as Pt, Protocol
from .room import Room, RoomManager


def shot_turn(method):
    @functools.wraps(method)
    def wrapper(socket, packet):
        if socket.player.seat == socket.player.room.whose_turn:
            method(socket, packet)
        else:
            logging.warning('Player[%d] TURN CHEAT', socket.uid)

    return wrapper


class SocketHandler(WebSocketHandler):

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.db: AsyncConnection = self.application.db
        self.player: Optional[Player] = None

    def data_received(self, chunk):
        logging.info('socket data_received')

    def get_current_user(self):
        return json_decode(self.get_secure_cookie("user"))

    @property
    def uid(self) -> int:
        return self.player.uid

    @property
    def room(self) -> Optional[Room]:
        return self.player.room

    @property
    def allow_robot(self) -> bool:
        return self.application.allow_robot

    @authenticated
    def open(self):
        user = self.current_user
        self.player = Player(user['uid'], user['username'], self)
        logging.info('SOCKET[%s] OPEN', self.player.uid)

    def on_close(self):
        self.player.leave_room()
        logging.info('SOCKET[%s] CLOSE', self.player.uid)

    async def on_message(self, message):
        packet = json.loads(message)
        logging.info('REQ[%d]: %s', self.uid, packet)

        code = packet[0]
        if code == Pt.REQ_LOGIN:
            response = [Pt.RSP_LOGIN, self.player.uid, self.player.name]
            await self.write_message(response)

        elif code == Pt.REQ_ROOM_LIST:
            await self.write_message([Pt.RSP_ROOM_LIST, RoomManager.get_waiting_rooms()])

        elif code == Pt.REQ_NEW_ROOM:
            # TODO: check player was already in a room.
            entrance_fee = packet[1]
            room = RoomManager.new_room(entrance_fee, self.allow_robot)
            self.player.join_room(room)
            logging.info('PLAYER[%s] NEW ROOM[%d]', self.uid, room.room_id)
            await self.write_message([Pt.RSP_NEW_ROOM, room.room_id])

        elif code == Pt.REQ_JOIN_ROOM:
            room_id, entrance_fee = packet[1], packet[2]
            room = RoomManager.find_waiting_room(room_id, entrance_fee, self.allow_robot)
            if not room:
                await self.write_message([Pt.RSP_ERROR, 'ROOM NOT FOUND'])
                logging.info('PLAYER[%d] JOIN ROOM[%d] NOT FOUND', self.uid, packet[1])
                return

            self.player.join_room(room)
            logging.info('PLAYER[%s] JOIN ROOM[%d]', self.uid, room.room_id)
            if room.is_full():
                room.deal_poker()
                RoomManager.on_room_changed(room)
                logging.info('ROOM[%s] GAME BEGIN[%s]', room.room_id, room.players)

        elif code == Pt.REQ_CALL_SCORE:
            self.handle_call_score(packet)

        elif code == Pt.REQ_DEAL_POKER:
            if self.player.room.state == 2:
                self.player.ready = True
            self.player.room.ready()

        elif code == Pt.REQ_SHOT_POKER:
            self.handle_shot_poker(packet)
        elif code == Pt.REQ_CHAT:
            self.handle_chat(packet)
        elif code == Pt.REQ_CHEAT:
            self.handle_cheat(packet[1])
        elif code == Pt.REQ_RESTART:
            self.player.room.reset()
        else:
            logging.info('UNKNOWN PACKET: %s', code)

    @shot_turn
    def handle_call_score(self, packet: List[Union[int, Any]]):
        score = packet[1]
        self.player.handle_call_score(score)

    @shot_turn
    def handle_shot_poker(self, packet: List[Union[int, Any]]):
        pokers = packet[1]
        self.player.handle_shot_poker(pokers)

    def handle_chat(self, packet: List[Union[int, Any]]):
        if self.player.room:
            self.player.room.handle_chat(self.player, packet[1])

    def handle_cheat(self, uid):
        for p in self.player.room.players:
            if p.uid == uid:
                self.player.send([Pt.RSP_CHEAT, p.uid, p.hand_pokers])

    def write_message(self, message: List[Union[Protocol, Any]], binary=False):
        if self.ws_connection is None:
            return
        packet = json.dumps(message)
        try:
            future = self.ws_connection.write_message(packet, binary=binary)
            logging.info('RSP[%d]: %s', self.uid, message)
        except WebSocketClosedError:
            logging.error('WebSockedClosed[%s][%s]', self.uid, message)

    # def send_updates(cls, chat):
    #     logging.info('sending message to %d waiters', len(cls.waiters))
    #     for waiter in cls.waiters:
    #         waiter.write_message('tornado:' + chat)


class LoopBackSocketHandler(SocketHandler):

    def __init__(self, player, **kwargs):
        self.player = player

    @property
    def allow_robot(self) -> bool:
        return True

    def write_message(self, message, binary=True):
        IOLoop.current().add_callback(self._write_message, message)
        return True

    def _write_message(self, packet):
        self.player.from_server(packet)


class AdminHandler(RestfulHandler):

    required_fields = ('allow_robot',)

    @authenticated
    def get(self):
        if self.current_user['uid'] != 1:
            self.send_error(403, reason='Forbidden')
            return
        self.write({'allow_robot': self.application.allow_robot})

    @authenticated
    def post(self):
        if self.current_user['uid'] != 1:
            self.send_error(403, reason='Forbidden')
            return
        self.application.allow_robot = bool(self.get_body_argument('allow_robot'))
        self.write({'allow_robot': self.application.allow_robot})
