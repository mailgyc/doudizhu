import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
TEMPLATE_ROOT = os.path.join(BASE_DIR, 'templates')

DEBUG = os.getenv('TORNADO_DEBUG') == 'True'

SECRET_KEY = os.getenv('SECRET_KEY', 'fiDSpuZ7QFe8fm0XP9Jb7ZIPNsOegkHYtgKSd4I83Hs=')

PORT = os.getenv('PORT', 8080)


def database_url(url):
    from urllib.parse import urlparse, ParseResult
    pr: ParseResult = urlparse(url)
    return {
        'host': pr.hostname,
        'database': pr.path[1:],
        'user': pr.username,
        'password': pr.password,
    }


DATABASE = database_url(os.getenv('DATABASE_URL', 'mysql://root:123456@127.0.0.1:3306/ddz'))

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'root': {
        'level': 'INFO',
        'handlers': ['console'],
        'propagate': True,
    },
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(module)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'tornado.general': {
            'handlers': ['console'],
            'propagate': True,
        },
    }
}


if os.getenv('SENTRY_DSN'):
    import sentry_sdk
    from sentry_sdk.integrations.tornado import TornadoIntegration
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        integrations=[TornadoIntegration()]
    )
