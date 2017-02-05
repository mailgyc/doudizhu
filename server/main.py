#!/usr/bin/env python
import concurrent.futures
import os.path

import motor
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket

from handler.game import GameHandler
from handler.web import WebHandler, AuthCreateHandler, AuthLoginHandler, AuthLogoutHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', WebHandler),
            (r'/auth/create', AuthCreateHandler),
            (r'/auth/login', AuthLoginHandler),
            (r'/auth/logout', AuthLogoutHandler),
            (r'/socket', GameHandler),
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
        self.executor = concurrent.futures.ThreadPoolExecutor()
        self.session = {}


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(8080)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
