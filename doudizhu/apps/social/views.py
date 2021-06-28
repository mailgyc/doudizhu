import hashlib
import json
import logging
from typing import Optional, Awaitable, Dict, Union

from tornado import httpclient
from tornado.escape import json_decode, json_encode
from tornado.web import RequestHandler

from apps.game.storage import Storage
from contrib.db import AsyncConnection
from contrib.handlers import JwtMixin
from settings import WECHAT_CONFIG
from .message import Msg

logger = logging.getLogger(__name__)

appid = WECHAT_CONFIG['appid']
appsecret = WECHAT_CONFIG['appsecret']


class WeChatConfig(RequestHandler):
    token = WECHAT_CONFIG['token']
    encoding_aes_key = WECHAT_CONFIG['encoding_aes_key']

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    @property
    def origin(self):
        return self.request.protocol + "://" + self.request.host

    def check_signature(self, signature, timestamp, nonce):
        params = sorted([self.token, timestamp, nonce])
        sha = hashlib.sha1()
        sha.update(''.join(params).encode('utf-8'))
        return signature == sha.hexdigest()

    async def get(self):
        signature = self.get_query_argument('signature')
        timestamp = self.get_query_argument('timestamp')
        nonce = self.get_query_argument('nonce')

        self.set_header('Content-Type', 'text/plain')
        if self.check_signature(signature, timestamp, nonce):
            self.write(self.get_query_argument('echostr', ''))
        else:
            self.write('Verify Failed')

    async def post(self):
        content = '感谢您的关注！'
        self.set_header('Content-Type', 'application/xml')
        response = Msg.parse_xml(self.request.body).to_xml(content)
        self.write(response)


class AuthHandler(RequestHandler, JwtMixin):

    @property
    def origin(self):
        return self.request.protocol + "://" + self.request.host

    async def get(self):
        code = self.get_query_argument('code', None)
        if code is None:
            self.clear_cookie('social')
            redirect = self.origin + '/social/index'
            url = f'https://open.weixin.qq.com/connect/oauth2/authorize?appid={appid}&redirect_uri={redirect}&response_type=code&scope=snsapi_userinfo#wechat_redirect'
            self.redirect(url)
        else:
            # 1. 从数据库获取用户信息
            current_user = await self.fetch_user_from_database()
            if not current_user:
                # 2. 从微信服务器获取用户信息
                current_user = await self.fetch_user_from_net(code)
                self.set_secure_cookie('social', json_encode(current_user), expires_days=7)

            payload = {
                **current_user,
                'room': Storage.find_player_room_id(current_user['uid']),
                'rooms': Storage.room_list(),
                'token': self.jwt_encode(current_user)
            }
            await self.render('index.html', payload=json.dumps(payload, ensure_ascii=False))

    async def fetch_user_from_database(self) -> Dict[str, Union[int, str]]:
        cookie = self.get_secure_cookie('social')
        if not cookie:
            return {}
        current_user = json_decode(cookie)
        if not current_user or not current_user.get('uid'):
            return {}
        db: AsyncConnection = self.application.db
        return await db.fetchone('SELECT id uid, username, sex, avatar FROM account WHERE id=%s', current_user['uid'])

    async def fetch_user_from_net(self, code) -> Dict[str, Union[int, str]]:
        access_token, openid, unionid = await self.fetch_access_token(code)
        response_json = await self.fetch_userinfo(access_token, openid)
        username = response_json.get('nickname')
        sex = response_json.get('sex')
        avatar = response_json.get('headimgurl')

        sql = '''INSERT INTO account (openid, username, sex, avatar) VALUES (%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE username=%s, sex=%s, avatar=%s'''

        db: AsyncConnection = self.application.db
        uid = await db.insert(sql, openid, username, sex, avatar, username, sex, avatar)
        if uid == 0:
            return await db.fetchone('SELECT id uid, username, sex, avatar FROM account WHERE openid=%s', openid)
        return {'uid': uid, 'username': username, 'sex': sex, 'avatar': avatar}

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    @staticmethod
    async def fetch_access_token(code: str):
        """
        第二步: 请求 access_token
        第三步：刷新 access_token（如果需要）
        {
            'access_token': '31_rKcMRyBvL_v8nA0vKtKzh6JA5nsF_31ddxBu3YxiWpvq1RPbZhO14Cgu5YfV9VsAQBSSd-NZ8J1GQC9qFG...',
            'refresh_token': '31_Z1qAEJrLV4DpOAlbtKpR8Nn8lu6cZpo673-mVks_sIY5mHN-hJT5PKD96CFKOxvcOdUvSkvvWeUYGOBa...',
            'expires_in': 7200,
            'scope': 'snsapi_userinfo',
            'openid': 'o5Nrmv0h-avFOKT7d91ZWO4vuMjU',
            'unionid': 'orfFiw80xGVWfCKMh4iNM6DTSoow'
        }
        :param code:
        :return:
        """
        url = f'https://api.weixin.qq.com/sns/oauth2/access_token?appid={appid}&secret={appsecret}&code={code}&grant_type=authorization_code'
        r = await async_http(url)
        return r.get('access_token'), r.get('openid'), r.get('unionid')

    @staticmethod
    async def fetch_userinfo(access_token, openid) -> Dict[str, Union[int, str]]:
        """
        第四步：拉取用户信息(需scope为 snsapi_userinfo)
        :param access_token:
        :param openid:
        :return:
        """
        url = f'https://api.weixin.qq.com/sns/userinfo?access_token={access_token}&openid={openid}&lang=zh_CN'
        return await async_http(url)


async def async_http(url):
    client = httpclient.AsyncHTTPClient()
    try:
        response = await client.fetch(url)
        logging.info('%s %s', url, response.body)
        return json.loads(response.body)
    except httpclient.HTTPError:
        logging.exception('HTTPError')
