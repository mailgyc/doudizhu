import asyncio
import logging
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Optional, Awaitable, Dict, Union, Any

import jwt
import orjson
from tornado.web import RequestHandler, HTTPError

from config import SECRET_KEY
from models.base import AlchemyMixin


class JwtMixin(object):

    @staticmethod
    def jwt_encode(payload: Dict[str, Union[str, int]]) -> str:
        expires = datetime.utcnow() + timedelta(seconds=3600)
        return jwt.encode({'exp': expires, **payload}, SECRET_KEY, algorithm='HS256')

    @staticmethod
    def jwt_decode(token) -> Optional[Dict[str, Union[str, int]]]:
        if not token:
            return None
        try:
            return jwt.decode(token, SECRET_KEY)
        except jwt.PyJWTError as e:
            logging.error('JWT', e)
            return None

    @staticmethod
    def parse_token(headers):
        header = headers.get('Authorization')
        if header:
            parts = header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                return parts[1]
        return None


class RestfulHandler(RequestHandler, AlchemyMixin):
    required_fields = ()

    def prepare(self):
        self.request.remote_ip = self.client_ip

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')
        self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.set_header('Access-Control-Allow-Headers', 'X-PINGOTHER, Content-Type')
        self.set_header('Access-Control-Allow-Credentials', 'true')

    def get_json_data(self) -> Dict[str, Any]:
        json_data: Dict[str, Any] = orjson.loads(self.request.body)
        if self.required_fields:
            for field in self.required_fields:
                if field not in json_data:
                    raise HTTPError(HTTPStatus.BAD_REQUEST, reason=f'The field "{field}" is required')
        return json_data

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        cookie = self.get_secure_cookie('userinfo')
        if cookie:
            return orjson.loads(cookie)
        return None

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        self.finish(orjson.dumps({"detail": self._reason}))

    @property
    def client_ip(self) -> str:
        headers = self.request.headers
        return headers.get('X-Forwarded-For', headers.get('X-Real-Ip', self.request.remote_ip))

    async def run_in_executor(self, func, *args):
        executor = self.application.executor
        return await asyncio.get_event_loop().run_in_executor(executor, func, *args)
