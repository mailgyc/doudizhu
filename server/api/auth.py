from typing import Optional, Awaitable

from sqlalchemy import select
from tornado.escape import json_encode
from tornado.web import authenticated, RequestHandler

from api.base import RestfulHandler, JwtMixin
from api.game.globalvar import GlobalVar
from models import User


class IndexHandler(RequestHandler):

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def get(self):
        self.render('poker.html')


class LoginHandler(RestfulHandler, JwtMixin):
    required_fields = ('name',)

    async def get(self):
        self.write({'detail': 'welcome'})

    async def post(self):
        name = self.get_json_data()['name']
        async with self.session as session:
            async with session.begin():
                account = await self.get_one_or_none(select(User).where(User.name == name))
                if not account:
                    account = User(openid=name, name=name, sex=1, avatar='')
                    session.add(account)
                    await session.commit()

        account = account.to_dict()
        self.set_secure_cookie('userinfo', json_encode(account))
        self.write({
            **account,
            'room': GlobalVar.find_player_room_id(account['uid']),
            'rooms': GlobalVar.room_list(),
            'token': self.jwt_encode(account)
        })


class UserInfoHandler(RestfulHandler):

    @authenticated
    async def get(self):
        account: User = await self.get_one_or_none(select(User).where(User.id == self.current_user['uid']))
        if account:
            account = account.to_dict()
            self.set_secure_cookie('user', json_encode(account))
            self.write({
                **account,
                'room': GlobalVar.find_player_room_id(account['uid']),
                'rooms': GlobalVar.room_list()
            })
        else:
            self.clear_cookie('userinfo')
            self.send_error(404, reason='User not found')


class LogoutHandler(RestfulHandler):

    @authenticated
    def post(self):
        self.clear_cookie('userinfo')
        self.write({})
