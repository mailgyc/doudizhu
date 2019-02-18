import sentry_sdk
from sentry_sdk.integrations.tornado import TornadoIntegration

from .base import *

DEBUG = False

SECRET_KEY = 'fiDSpuZ7QFe8fm0XP9Jb7ZIPNsOegkHYtgKSd4I83Hs='

DATABASE = {
    'host': 'localhost',
    'database': 'ddz',
    'user': 'root',
    'password': '123456',
}

sentry_sdk.init(
    'https://f32173ee60f949d5b2cbad5c651a14a7@sentry.io/1366504',
    integrations=[TornadoIntegration()]
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
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
            'level': 'INFO',
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
        'doudizhu': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False,
        },
    },
}
