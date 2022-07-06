import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
TEMPLATE_ROOT = os.path.join(BASE_DIR, 'templates')

DEBUG = os.getenv('TORNADO_DEBUG') == 'True'

SECRET_KEY = os.getenv('SECRET_KEY', 'fiDSpuZ7QFe8fm0XP9Jb7ZIPNsOegkHYtgKSd4I83Hs=')

PORT = os.getenv('PORT', 8080)

WECHAT_CONFIG = {
    'appid': os.getenv('APPID'),
    'appsecret': os.getenv('APPSECRET'),
    'token': os.getenv('TOKEN'),
    'encoding_aes_key': os.getenv('ENCODING_AES_KEY'),
}

DATABASE_URI = os.getenv('DATABASE_URI', 'mysql+aiomysql://root:123456@127.0.0.1:3306/ddz')

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
            'format': '%(asctime)s %(levelname)s %(module)s %(lineno)d %(message)s'
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