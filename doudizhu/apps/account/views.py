from typing import Optional, Awaitable

from tornado.escape import json_encode
from tornado.web import authenticated, RequestHandler

from apps.game.storage import Storage
from contrib.handlers import RestfulHandler, JwtMixin


class IndexHandler(RequestHandler):

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def get(self):
        self.render('poker.html')


class LoginHandler(RestfulHandler, JwtMixin):
    required_fields = ('username',)

    async def post(self):
        username = self.json.get('username')

        account = await self.db.fetchone('SELECT id uid, username, sex, avatar FROM account WHERE username=%s', username)
        if not account:
            uid = await self.db.insert(
                'INSERT INTO account (openid, username, sex, avatar) VALUES (%s,%s,%s,%s)', username, username, 1, '')
            account = {'uid': uid, 'username': username, 'sex': 1, 'avatar': ''}

        self.set_secure_cookie('userinfo', json_encode(account))
        self.write({
            **account,
            'room': Storage.find_player_room_id(account['uid']),
            'rooms': Storage.room_list(),
            'token': self.jwt_encode(account)
        })


class UserInfoHandler(RestfulHandler):

    @authenticated
    async def get(self):
        account = await self.db.fetchone('SELECT id uid, username, sex, avatar FROM account WHERE id=%s',
                                         self.current_user['uid'])
        if not account:
            self.clear_cookie('userinfo')
            self.send_error(404, reason='User not found')
            return

        self.set_secure_cookie('user', json_encode(account))
        self.write({
            **account,
            'room': Storage.find_player_room_id(account['uid']),
            'rooms': Storage.room_list()
        })


class LogoutHandler(RestfulHandler):

    @authenticated
    def post(self):
        self.clear_cookie('userinfo')
        self.write({})
