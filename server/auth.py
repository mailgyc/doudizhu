import bcrypt
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado import gen

from base import BaseHandler


class AuthCreateHandler(BaseHandler):

    def get(self):
        self.render("auth_register.htm")

    @gen.coroutine
    def post(self):
        account = yield self.db.account.find_one({'email': self.get_argument('email')})
        if account:
            raise tornado.web.HTTPError(400, "email already created")

        hashed_password = yield self.executor.submit(
            bcrypt.hashpw, tornado.escape.utf8(self.get_argument("password")),
            bcrypt.gensalt())

        result = self.db.account.insert_one({
            'email': self.get_argument("email"),
            'from': 'WEB',
            'hashed_password': hashed_password, })
        self.set_secure_cookie("uid", str(result.inserted_id))

        self.db.player.insert_one({
            'account_id': result.inserted_id,
            'coin': self.settings.get('init_coin', 1000),
            'nickname': self.get_argument('name'),
        })
        
        self.redirect(self.get_argument("next", "/"))


class AuthLoginHandler(BaseHandler):

    @gen.coroutine
    def get(self):
        self.render("auth_login.htm", error=None)

    @gen.coroutine
    def post(self):
        account = yield self.db.account.find_one({'email': self.get_argument('email')})
        if not account:
            self.render("auth_login.htm", error="email not found")
            return

        hashed_password = yield self.executor.submit(
            bcrypt.hashpw, tornado.escape.utf8(self.get_argument("password")),
            tornado.escape.utf8(account.get('hashed_password')))

        if hashed_password == account.get('hashed_password', ''):
            self.set_secure_cookie("uid", str(account.get('_id')))
            self.redirect(self.get_argument("next", "/"))
        else:
            self.render("auth_login.htm", error="incorrect password")


class AuthLogoutHandler(BaseHandler):

    def get(self):
        self.clear_cookie("uid")
        self.redirect(self.get_argument("next", "/"))


