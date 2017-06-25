import logging
import os.path
from concurrent.futures import ThreadPoolExecutor

import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
from net.socket import SocketHandler
from net.web import WebHandler
from db import torndb

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ddz')
logger.setLevel(logging.DEBUG)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', WebHandler),
            (r'/ws', SocketHandler),
        ]
        settings = dict(
            title='Tornado Poker',
            cookie_secret='fiDSpuZ7QFe8fm0XP9Jb7ZIPNsOegkHYtgKSd4I83Hs=',
            template_path=os.path.join(BASE_DIR, 'static'),
            static_path=os.path.join(BASE_DIR, 'static'),
            login_url='/',
            xsrf_cookies=True,
            debug=True,
        )
        super(Application, self).__init__(handlers, **settings)
        self.db = torndb.Connection(
            host='localhost',
            database='ddz',
            user='root',
            password='123123')
        self.executor = ThreadPoolExecutor()


def main():
    logger.info('http://127.0.0.1:8080')
    tornado.options.parse_command_line()
    app = Application()
    app.listen(8080)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()

