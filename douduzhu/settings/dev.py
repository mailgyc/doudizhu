from .base import *

SECRET_KEY = 'fiDSpuZ7QFe8fm0XP9Jb7ZIPNsOegkHYtgKSd4I83Hs='

DATABASE = {
    'host': 'localhost',
    'database': 'ddz',
    'user': 'root',
    'password': '123456',
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'INFO',
        'handlers': ['console'],
    },
    'formatters': {
        'simple': {
            'format': '%(asctime).16s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        'doudizhu': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}
