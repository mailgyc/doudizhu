import json
import logging
from typing import Optional, List, Union, Any

from tornado.escape import json_decode
from tornado.web import authenticated
from tornado.websocket import WebSocketHandler, WebSocketClosedError

from contrib.db import AsyncConnection
from contrib.handlers import RestfulHandler
from .player import Player
from .protocol import Protocol
from .room import Room


class SocketHandler(WebSocketHandler):

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.db: AsyncConnection = self.application.db
        self.player: Optional[Player] = None

    async def get(self, *args: Any, **kwargs: Any) -> None:
        self.request.headers['origin'] = None
        self.request.headers['Sec-Websocket-Origin'] = None
        await super().get(*args, **kwargs)

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

    def on_message(self, message):
        packet = json.loads(message)
        logging.info('REQ[%d]: %s', self.uid, packet)

        self.player.on_message(packet)

    def on_close(self):
        self.player.leave_room()
        logging.info('SOCKET[%s] CLOSE', self.player.uid)

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
