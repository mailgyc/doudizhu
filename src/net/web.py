import json
import subprocess
from concurrent.futures import ThreadPoolExecutor

import bcrypt
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.web import RequestHandler

from db import torndb
from core.player import Player


class BaseHandler(RequestHandler):
    @property
    def db(self) -> torndb.Connection:
        return self.application.db

    @property
    def executor(self) -> ThreadPoolExecutor:
        return self.application.executor

    def data_received(self, chunk):
        pass

    def on_finish(self):
        # self.session.flush()
        pass


class WebHandler(BaseHandler):
    # @tornado.web.authenticated
    def get(self):
        if not self.get_cookie("_csrf"):
            self.set_cookie("_csrf", self.xsrf_token)
        self.render('poker.html')


class UpdateHandler(BaseHandler):
    def get(self):
        proc = subprocess.run(["git", "pull"], stdout=subprocess.PIPE)
        self.head('content-type', 'text/plain; charset=UTF-8')
        self.write(proc.stdout)


class RegHandler(BaseHandler):

    def post(self):
        email = self.get_argument('email', self.get_argument('username'))
        account = self.db.get('SELECT * FROM account WHERE email="%s"', email)
        if account:
            raise tornado.web.HTTPError(400, "username already taken")

        username = self.get_argument('username')
        password = self.get_argument('password')
        password = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())

        uid = self.db.insert('INSERT INTO account (email, username, password) VALUES ("%s", "%s", "%s")',
                             email, username, password)

        self.set_secure_cookie("uid", str(account.get('id')))
        self.write('ok')


class LoginHandler(BaseHandler):

    def post(self):
        username = self.get_argument('email')
        password = self.get_argument("password")
        account = self.db.get('SELECT * FROM account WHERE email="%s"', self.get_argument('email'))
        password = bcrypt.hashpw(password.encode('utf8'), account.get('password'))

        self.head('content-type', 'application/json')
        if password == account.get('password'):
            self.set_secure_cookie("uid", str(account.get('id')))
            self.redirect(self.get_argument("next", "/"))


class LoginoutHandler(BaseHandler):

    def post(self):
        uid = self.get_secure_cookie("uid")
        self.clear_cookie("uid")
        self.session.remove(int(uid))
        self.redirect(self.get_argument("next", "/"))
