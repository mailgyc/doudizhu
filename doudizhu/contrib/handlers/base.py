import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Awaitable, Dict, Union, Any

import jwt
from tornado.escape import json_encode, json_decode
from tornado.web import RequestHandler, HTTPError

from contrib.db import AsyncConnection
from settings import SECRET_KEY


class JwtMixin(object):

    @staticmethod
    def jwt_encode(payload: Dict[str, Union[str, int]]) -> str:
        expires = datetime.utcnow() + timedelta(seconds=3600)
        token = jwt.encode({'exp': expires, **payload}, SECRET_KEY, algorithm='HS256')
        return token.decode('ascii')

    @staticmethod
    def jwt_decode(token) -> Optional[Dict[str, Union[str, int]]]:
        if not token:
            return None
        try:
            return jwt.decode(token, SECRET_KEY)
        except jwt.PyJWTError as e:
            logging.exception('JWT AUTH', e)
            return None

    @staticmethod
    def parse_token(headers):
        header = headers.get('Authorization')
        if header:
            parts = header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                return parts[1]
        return None


class RestfulHandler(RequestHandler):
    required_fields = []

    def prepare(self):
        self.request.remote_ip = self.client_ip
        if self.request.body and self.request.headers.get('Content-Type') == 'application/json':
            args = json_decode(self.request.body)
            if self.required_fields:
                for field in self.required_fields:
                    if field not in args:
                        raise HTTPError(403, reason=f'The field "{field}" is required')
            setattr(self, '_post_json', args)

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')
        self.set_header('Access-Control-Allow-Origin', self.request.headers.get('origin', '*'))
        self.set_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.set_header('Access-Control-Allow-Headers', 'X-PINGOTHER, Content-Type')
        self.set_header('Access-Control-Allow-Credentials', "true")

    @property
    def json(self):
        return getattr(self, '_post_json', {})

    def options(self):
        self.set_status(204)

    def get_current_user(self):
        user = self.get_secure_cookie('user')
        if user:
            return json_decode(user)
        return None

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        pass

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        self.finish(json_encode({"detail": self._reason}))

    @property
    def db(self) -> AsyncConnection:
        return self.application.db

    @property
    def client_ip(self) -> str:
        headers = self.request.headers
        return headers.get('X-Forwarded-For', headers.get('X-Real-Ip', self.request.remote_ip))

    async def run_in_executor(self, func, *args):
        executor = self.application.executor
        return await asyncio.get_event_loop().run_in_executor(executor, func, *args)
