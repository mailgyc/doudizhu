from typing import Optional, Awaitable

import bcrypt
import pymysql
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
    required_fields = ('username', 'password')

    async def post(self):
        email = self.json.get('username')
        password = self.json.get("password")

        account = await self.db.fetchone('SELECT id, username, password FROM account WHERE email=%s', email)
        if not account:
            self.send_error(400, reason='This email address does not exist.')
            return

        verify_pass = await self.run_in_executor(bcrypt.checkpw, password.encode('utf8'),
                                                 account.get('password').encode('utf8'))
        if not verify_pass:
            self.send_error(400, reason='Incorrect username or password.')

        uid, username = account.get('id'), account.get('username')
        self.set_secure_cookie('user', json_encode({'uid': uid, 'username': username}))
        self.write({
            'uid': uid,
            'username': username,
            'room': Storage.find_player_room_id(uid),
            'rooms': Storage.room_list(),
            'token': self.jwt_encode({'uid': uid, 'username': username})
        })


class UserInfoHandler(RestfulHandler):

    @authenticated
    async def get(self):
        account = await self.db.fetchone('SELECT id, username FROM account WHERE id=%s', self.current_user['uid'])
        if not account:
            self.clear_cookie('user')
            self.send_error(404, reason='User not found')
            return

        uid, username = account.get('id'), account.get('username')
        self.set_secure_cookie('user', json_encode({'uid': uid, 'username': username}))
        self.write({'uid': uid, 'username': username, 'room': Storage.find_player_room_id(uid)})


class SignupHandler(RestfulHandler):
    required_fields = ('email', 'username', 'password', 'password_repeat')

    async def post(self):
        email = self.json.get('email')
        username = self.json.get('username')
        password = self.json.get('password')
        password_repeat = self.json.get('password_repeat')
        if password != password_repeat:
            self.send_error(400, reason='The password does not match')
            return

        try:
            uid = await self.create_account(username, email, password)
            self.set_secure_cookie('user', json_encode({'uid': uid, 'username': username}))
            self.write({'uid': uid, 'username': username})
        except pymysql.IntegrityError as e:
            if await self.account_exists(email):
                self.send_error(400, reason='An account with this email address already exists.')
            else:
                raise e

    async def create_account(self, username, email, password) -> int:
        password = await self.run_in_executor(bcrypt.hashpw, password.encode('utf8'), bcrypt.gensalt())
        return await self.db.insert('INSERT INTO account (email, username, password, ip_addr) VALUES (%s,%s,%s,%s)',
                                    email, username, password, self.client_ip)

    async def account_exists(self, email) -> bool:
        account = await self.db.fetchone('SELECT id FROM account WHERE email=%s', email)
        return True if account else False


class LogoutHandler(RestfulHandler):

    @authenticated
    def post(self):
        self.clear_cookie('user')
        self.write({})
