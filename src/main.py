import logging
import os.path
from concurrent.futures import ThreadPoolExecutor

import tornado.escape
import tornado.ioloop
from tornado.options import define, options
import tornado.web
import tornado.websocket
from net.socket import SocketHandler
from net.web import WebHandler, UpdateHandler, RegHandler
from db import torndb

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


define("host", default="localhost", help="DB host")
define("database", default="ddz", help="DB used")
define("user", default="root", help="DB username")
define("password", default="123123", help="DB Password")


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', WebHandler),
            (r'/update', UpdateHandler),
            (r'/reg', RegHandler),
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
        tornado.options.parse_config_file("server.conf")
        super(Application, self).__init__(handlers, **settings)
        self.db = torndb.Connection(
            host=options.host,
            database=options.database,
            user=options.user,
            password=options.password)
        self.executor = ThreadPoolExecutor()


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(8080)
    tornado.ioloop.IOLoop.current().start()
    logger.info('listening on 8080')


if __name__ == '__main__':
    main()

