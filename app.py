import logging
import tornado.escape
import tornado.ioloop
import tornado.web
import tornado.websocket
import os.path
import uuid

from tornado.options import define, options

define('port', default=8000, help='run on the given port', type=int)
define('debug', default=True, help='run in debug mode')

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/socket", SocketHandler),
        ]
        settings = dict(
            cookie_secret = "poker-601743bb-3c82-4fe6-b27f-a1159f04c4f",
            static_path  = os.path.join(os.path.dirname(__file__), 'static'),
            xsrf_cookies = True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')


class SocketHandler(tornado.websocket.WebSocketHandler):
    waiters = set()
    cache = []
    cache_size = 200

    def get_compression_options(self):
        return {}

    def open(self):
        SocketHandler.waiters.add(self)

    def on_close(self):
        SocketHandler.waiters.remove(self)

    @classmethod
    def update_cache(cls, chat):
        cls.cache.append(chat)
        if len(cls.cache) > cls.cache_size:
            cls.cache = cls.cache[-cls.cache_size:]

    @classmethod
    def send_updates(cls, chat):
        logging.info('sending message to %d waiters', len(cls.waiters))
        for waiter in cls.waiters:
            try:
                waiter.write_message('tornado:' + chat)
            except:
                logging.error('Error sending message', exc_info=True)

    def on_message(self, message):
        logging.info('got message %r', message)
        #parsed = tornado.escapt.json_decode(message)

        SocketHandler.update_cache(message)
        SocketHandler.send_updates(message)


def main():
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()

if  __name__ == '__main__':
    main()


