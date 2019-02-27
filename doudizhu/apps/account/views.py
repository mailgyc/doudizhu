import bcrypt

from contrib.handlers import BaseHandler


class HomeHandler(BaseHandler):

    def get(self):
        if not self.get_cookie("_csrf"):
            self.set_cookie("_csrf", self.xsrf_token)
        # user = xhtml_escape(self.current_user or '')
        user = self.current_user or ''
        self.render('poker.html', user=user)


class SignupHandler(BaseHandler):

    async def post(self):
        email = self.get_query_params('email', self.get_query_params('username'))
        account = await self.db.fetchone('SELECT id FROM account WHERE email=%s', email)
        if account:
            self.write({'errcode': 1, 'errmsg': 'The email has already exist'})
            return

        username = self.get_query_params('username')
        password = self.get_query_params('password')
        password = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())

        uid = await self.db.insert('INSERT INTO account (email, username, password, ip_addr) VALUES (%s, %s, %s, %s)',
                                   email, username, password, self.client_ip)
        self.set_current_user(uid, username)
        self.set_header('Content-Type', 'application/json')
        response = {
            'errcode': 0,
            'userinfo': {'uid': uid, 'username': username}
        }
        self.write(response)


class LoginHandler(BaseHandler):

    async def post(self):
        email = self.get_argument('email')
        password = self.get_argument("password")
        account = await self.db.fetchone('SELECT * FROM account WHERE email=%s', email)
        password = bcrypt.hashpw(password.encode('utf8'), account.get('password'))

        self.set_header('Content-Type', 'application/json')
        if password == account.get('password'):
            self.set_current_user(account.get('id'), account.get('username'))
            self.redirect(self.get_argument("next", "/"))


class LogoutHandler(BaseHandler):

    def post(self):
        self.clear_cookie('user')
        self.redirect(self.get_argument("next", "/"))
