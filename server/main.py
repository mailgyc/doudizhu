#!/usr/bin/env python
import concurrent.futures
import logging
import motor
import redis
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os.path

from tornado.options import define, options
from auth import AuthCreateHandler, AuthLoginHandler, AuthLogoutHandler
from base import BaseHandler
from game import SocketHandler

# import base64, uuid
# base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)

# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print(BASE_DIR)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', MainHandler),
            (r'/auth/create', AuthCreateHandler),
            (r'/auth/login', AuthLoginHandler),
            (r'/auth/logout', AuthLogoutHandler),
            (r'/socket', SocketHandler),
        ]
        settings = dict(
            title='Tornado Poker',
            init_coin=4000,
            xsrf_cookies=True,
            cookie_secret='fiDSpuZ7QFelfm0XP9Jb7ZIPNsOegkHYtgKSd4I83Hs=',
            template_path=os.path.join(BASE_DIR, 'templates'),
            static_path=os.path.join(BASE_DIR, 'static'),
            login_url='/auth/login',
            debug=True,
        )
        super(Application, self).__init__(handlers, **settings)
        self.db = motor.motor_tornado.MotorClient('mongodb://localhost:27017/').poker
        self.redis = redis.StrictRedis(host='127.0.0.1', port=6379)
        self.executor = concurrent.futures.ThreadPoolExecutor(2),


class MainHandler(BaseHandler):

    # @tornado.web.authenticated
    def get(self):
        self.render('poker.htm')


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(8080)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()

