import json
from concurrent.futures import ThreadPoolExecutor

from raven.contrib.tornado import SentryMixin
from tornado.escape import json_encode
from tornado.web import RequestHandler

from contrib.db import AsyncConnection


class BaseHandler(SentryMixin, RequestHandler):

    @property
    def db(self) -> AsyncConnection:
        return self.application.db

    @property
    def executor(self) -> ThreadPoolExecutor:
        return self.application.executor

    @property
    def client_ip(self):
        headers = self.request.headers
        return headers.get('X-Forwarded-For', headers.get('X-Real-Ip', self.request.remote_ip))

    def data_received(self, chunk):
        pass

    def get_query_params(self, name, default=None, strip=True):
        if not hasattr(self, 'query_params'):
            query_params = json.loads(self.request.body.decode('utf-8'))
            setattr(self, 'query_params', query_params)
        return self.query_params.get(name, default)

    def get_current_user(self):
        return self.get_secure_cookie('user')

    def set_current_user(self, uid, username):
        info = {
            'uid': uid,
            'username': username,
        }
        self.set_secure_cookie('user', json_encode(info))

    def on_finish(self):
        # self.session.flush()
        pass
