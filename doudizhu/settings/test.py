import os

from .base import * 


TEST_DB_PATH = os.path.join(PROJECT_DIR, 'test_db.db')

DATABASES = {
    'default': {
        'ENGINE': 'sqlite',
        'NAME': TEST_DB_PATH
    }
}
