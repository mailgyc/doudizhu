import hashlib
import json
import logging
import time
from typing import Optional, Awaitable, Dict, Union
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from tornado import httpclient
from tornado.escape import json_decode, json_encode
from tornado.web import RequestHandler

from api.base import JwtMixin
from api.game.globalvar import GlobalVar
from config import WECHAT_CONFIG
from models.base import AlchemyMixin
from models import User

logger = logging.getLogger(__name__)

appid = WECHAT_CONFIG['appid']
appsecret = WECHAT_CONFIG['appsecret']


class WechatConfig(RequestHandler):
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


class WechatHandler(RequestHandler, AlchemyMixin, JwtMixin):

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
                'room': GlobalVar.find_player_room_id(current_user['uid']),
                'rooms': GlobalVar.room_list(),
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
        account: User = await self.get_one_or_none(select(User).where(User.id == current_user['uid']))
        return account.to_dict() if account else {}

    async def fetch_user_from_net(self, code) -> Dict[str, Union[int, str]]:
        access_token, openid, unionid = await self.fetch_access_token(code)
        response_json = await self.fetch_userinfo(access_token, openid)
        name = response_json.get('nickname')
        sex = response_json.get('sex')
        avatar = response_json.get('headimgurl')

        insert_stmt = insert(User).values(openid=openid, name=name, sex=sex, avatar=avatar)
        uid = await self.insert_or_update(
            insert_stmt,
            name=insert_stmt.inserted.name,
            sex=insert_stmt.inserted.sex,
            avatar=insert_stmt.inserted.avatar,
        )
        if uid == 0:
            uid = (await self.get_one_or_none(select(User).where(User.openid == openid))).id
        return {'uid': uid, 'name': name, 'sex': sex, 'avatar': avatar}

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


class Msg(object):

    @staticmethod
    def parse_xml(data: str) -> Optional['Msg']:
        if len(data) == 0:
            return None
        xml = ElementTree.fromstring(data)
        msg_type = xml.find('MsgType').text

        factory = {'text': TextMsg, 'image': ImageMsg}
        return factory.get(msg_type).from_xml(xml)

    def __init__(self, *args, **kwargs):
        self.ToUserName = None
        self.FromUserName = None
        self.CreateTime = None
        self.MsgType = None
        self.MsgId = None

    def from_xml(self, xml: Element):
        self.ToUserName = xml.find('ToUserName').text
        self.FromUserName = xml.find('FromUserName').text
        self.CreateTime = xml.find('CreateTime').text
        self.MsgType = xml.find('MsgType').text
        self.MsgId = xml.find('MsgId').text
        return self

    def to_xml(self, *args, **kwargs):
        pass

    @property
    def timestamp(self):
        return int(time.time())


class TextMsg(Msg):

    def __init__(self):
        super().__init__()
        self.Content = None

    def from_xml(self, xml: Element):
        super().from_xml(xml)
        self.Content = xml.find('Content').text.encode("utf-8")
        return self

    def to_xml(self, content):
        return f"""<xml>
            <ToUserName><![CDATA[{self.FromUserName}]]></ToUserName>
            <FromUserName><![CDATA[{self.ToUserName}]]></FromUserName>
            <CreateTime>{self.timestamp}</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[{content}]]></Content>
        </xml>"""


class ImageMsg(Msg):
    def __init__(self):
        super().__init__()
        self.PicUrl = None
        self.MediaId = None

    def from_xml(self, xml: Element):
        self.PicUrl = xml.find('PicUrl').text
        self.MediaId = xml.find('MediaId').text
        return self

    def to_xml(self, media):
        return f"""<xml>
            <ToUserName><![CDATA[{self.FromUserName}]]></ToUserName>
            <FromUserName><![CDATA[{self.ToUserName}]]></FromUserName>
            <CreateTime>{self.timestamp}</CreateTime>
            <MsgType><![CDATA[image]]></MsgType>
            <Image>
            <MediaId><![CDATA[{media}]]></MediaId>
            </Image>
        </xml>"""
