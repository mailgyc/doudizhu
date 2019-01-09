import os

import tornado.template
from tornado.options import define, options

define("port", default=8080, help="run on the given port", type=int)
define("debug", default=True, help="debug mode")
define("host", default="localhost", help="Database host")
define("database", default="ddz", help="Database name")
define("user", default="root", help="username")
define("password", default="123456", help="password")
tornado.options.parse_command_line()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
TEMPLATE_ROOT = os.path.join(BASE_DIR, 'templates')

APPLICATION = {
    'title': 'Tornado Poker',
    'login_url': '/',
    'static_path': STATIC_ROOT,
    'template_path': TEMPLATE_ROOT,
    'xsrf_cookies': True,
    'cookie_secret': 'fiDSpuZ7QFe8fm0XP9Jb7ZIPNsOegkHYtgKSd4I83Hs=',
    'debug': options.debug,
}

if not options.debug:
    import sentry_sdk
    from sentry_sdk.integrations.tornado import TornadoIntegration
    sentry_sdk.init(
        'https://f32173ee60f949d5b2cbad5c651a14a7@sentry.io/1366504',
        integrations=[TornadoIntegration()]
    )


DATABASE = {
    'host': options.host,
    'database': options.database,
    'user': options.user,
    'password': options.password,
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'root': {
        'level': 'INFO',
        'handlers': ['file', 'console'],
    },
    'formatters': {
        'simple': {
            'format': '%(asctime).19s %(message)s'
        },
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'filename': 'ddz.log',
            'class': 'logging.FileHandler',
        },
    },
    'loggers': {
        '': {
            'level': 'INFO',
            'handlers': ['file'],
            'propagate': False,
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False,
        },
    },
}
