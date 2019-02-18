import os
os.environ.setdefault('TORNADO_SETTINGS_MODULE', 'settings.test')

import pytest

from app import make_app

from contrib.db import session
from contrib.db import Model

from mixer.backend.sqlalchemy import Mixer


@pytest.fixture
def app(request):
    return make_app()


@pytest.fixture
def mixer():
    return Mixer(session=session)


@pytest.fixture(autouse=True)
def db(request):
    Model.create_all()

    def teardown():
        Model.drop_all()

    request.addfinalizer(teardown)
