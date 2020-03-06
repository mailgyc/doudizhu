import json
import logging
from typing import Optional, Any, Dict, List, Union

from tornado.escape import json_decode
from tornado.web import authenticated
from tornado.websocket import WebSocketHandler, WebSocketClosedError

from contrib.db import AsyncConnection
from contrib.handlers import RestfulHandler, JwtMixin
from .player import Player
from .protocol import Protocol
from .room import Room
from .storage import Storage


class SocketHandler(WebSocketHandler, JwtMixin):

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.db: AsyncConnection = self.application.db
        self.player: Optional[Player] = None

    def get_current_user(self):
        token = self.get_argument('token', None)
        if token:
            return self.jwt_decode(token)
        cookie = self.get_secure_cookie("user")
        if cookie:
            return json_decode(cookie)
        return None

    @property
    def uid(self) -> int:
        return self.player.uid

    @property
    def room(self) -> Optional[Room]:
        return self.player.room

    @property
    def allow_robot(self) -> bool:
        return self.application.allow_robot

    async def data_received(self, chunk):
        logging.info('Received stream data')

    @authenticated
    async def open(self):
        user = self.current_user
        self.player = Storage.find_or_create_player(user['uid'], user['username'])
        self.player.socket = self
        logging.info('SOCKET[%s] OPEN', self.player.uid)

    def on_message(self, message):
        if message == 'ping':
            self._write_message('pong')
            return

        code, packet = self.decode_message(message)
        if code is None:
            self.write_message([Protocol.ERROR, {'reason': 'Protocol cannot be resolved'}])
            return

        logging.info('REQ[%d]: %s', self.uid, message)

        if code == Protocol.REQ_ROOM_LIST:
            self.write_message([Protocol.RSP_ROOM_LIST, {'rooms': Storage.room_list()}])
            return

        self.player.on_message(code, packet)

    @staticmethod
    def decode_message(message):
        try:
            code, packet = json.loads(message)
            if isinstance(code, int) and isinstance(packet, dict):
                return code, packet
        except (json.decoder.JSONDecodeError, ValueError):
            logging.error('ERROR MESSAGE: %s', message)
        return None, None

    def on_close(self):
        self.player.on_disconnect()
        logging.info('SOCKET[%s] CLOSED[%s %s]', self.player.uid, self.close_code, self.close_reason)

    def check_origin(self, origin: str) -> bool:
        return True

    def get_compression_options(self) -> Optional[Dict[str, Any]]:
        return {'compression_level': 6, 'mem_level': 9}

    def write_message(self, message: List[Union[Protocol, Dict[str, Any]]], binary=False):
        packet = json.dumps(message)
        self._write_message(packet, binary)

    def _write_message(self, message, binary=False):
        if self.ws_connection is None:
            return
        try:
            future = self.ws_connection.write_message(message, binary=binary)
            logging.info('RSP[%d]: %s', self.uid, message)
        except WebSocketClosedError:
            logging.error('WebSockedClosed[%s][%s]', self.uid, message)


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
