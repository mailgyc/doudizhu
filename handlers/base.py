from concurrent.futures import ThreadPoolExecutor

from tornado.escape import json_encode
from tornado.web import RequestHandler

from db import torndb


class BaseHandler(RequestHandler):

    @property
    def db(self) -> torndb.Connection:
        return self.application.db

    @property
    def executor(self) -> ThreadPoolExecutor:
        return self.application.executor

    def data_received(self, chunk):
        pass

    def get_current_user(self):
        return self.get_secure_cookie("user")

    def set_current_user(self, uid, username):
        info = {
            'uid': uid,
            'username': username,
        }
        self.set_secure_cookie('user', json_encode(info))

    def on_finish(self):
        # self.session.flush()
        pass
