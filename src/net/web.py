import subprocess

import bcrypt
from tornado.escape import json_encode

from net.base import BaseHandler


class WebHandler(BaseHandler):
    def get(self):
        if not self.get_cookie("_csrf"):
            self.set_cookie("_csrf", self.xsrf_token)
        # user = xhtml_escape(self.current_user or '')
        user = self.current_user or ''
        self.render('poker.html', user=user)


class UpdateHandler(BaseHandler):
    # @tornado.web.authenticated
    def get(self):
        proc = subprocess.run(["git", "pull"], stdout=subprocess.PIPE)
        self.set_header('Content-Type', 'text/plain; charset=UTF-8')
        self.write(proc.stdout)


class RegHandler(BaseHandler):

    def post(self):
        email = self.get_argument('email', self.get_argument('username'))
        account = self.db.get('SELECT * FROM account WHERE email="%s"', email)

        if account:
            self.write('1')
            return

        username = self.get_argument('username')
        password = self.get_argument('password')
        password = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())

        uid = self.db.insert('INSERT INTO account (email, username, password) VALUES ("%s", "%s", "%s")',
                             email, username, password)

        self.set_current_user(uid, username)
        self.set_header('Content-Type', 'application/json')
        info = {
            'uid': uid,
            'username': username,
        }
        self.write(json_encode(info))


class LoginHandler(BaseHandler):

    def post(self):
        email = self.get_argument('email')
        password = self.get_argument("password")
        account = self.db.get('SELECT * FROM account WHERE email="%s"', email)
        password = bcrypt.hashpw(password.encode('utf8'), account.get('password'))

        self.set_header('Content-Type', 'application/json')
        if password == account.get('password'):
            self.set_current_user(account.get('id'), account.get('username'))
            self.redirect(self.get_argument("next", "/"))


class LogoutHandler(BaseHandler):

    def post(self):
        self.clear_cookie('user')
        self.redirect(self.get_argument("next", "/"))
