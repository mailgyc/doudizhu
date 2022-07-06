from typing import Optional, Awaitable

from sqlalchemy import select
from tornado.escape import json_encode
from tornado.web import authenticated, RequestHandler

from apps.account.models import Account
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
        async with self.session as session:
            async with session.begin():
                account = await self.get_one_or_none(select(Account).where(Account.username == username))
                if not account:
                    account = Account(openid=username, username=username, sex=1, avatar='')
                    session.add(account)
                    await session.commit()

        account = account.to_dict()
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
        account: Account = await self.get_one_or_none(select(Account).where(Account.id == self.current_user['uid']))
        if account:
            account = account.to_dict()
            self.set_secure_cookie('user', json_encode(account))
            self.write({
                **account,
                'room': Storage.find_player_room_id(account['uid']),
                'rooms': Storage.room_list()
            })
        else:
            self.clear_cookie('userinfo')
            self.send_error(404, reason='User not found')


class LogoutHandler(RestfulHandler):

    @authenticated
    def post(self):
        self.clear_cookie('userinfo')
        self.write({})
