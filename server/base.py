import json
import redis
import tornado.web
import tornado.websocket
import tornadoredis
from bson import ObjectId


class SessionMixin(object):

    @property
    def session(self):
        # if not hasattr(self,  '__session_manager'):
        #     setattr(self,  '__session_manager', RedisSession(self))
        # return getattr(self,  '__session_manager')
        pass


class Room(object):

    # def __init__(self, redis):
    #     self.redis = redis
    def __init__(self):
        self.redis = redis.StrictRedis()
        self.client = tornadoredis.Client()

    @property
    def waiting_tables(self):
        value = self.redis.get('waiting_tables')
        waiting_tables = value.decode('utf-8') if value else ''
        return json.loads(waiting_tables)

    @property
    def join_tables(self, tid):
        lock = self.redis.lock('waiting_tables_lock')
        try:
            lock.acquire(blocking=True)
            tables = self.waiting_tables
            for table in self.tables:
                if tid != table[0]:
                    continue

                table.append(tid)
                if len(table) == 4:
                    tables.remove(table)
                    redis.set('waiting_tables', json.dumps(tables))
                return True
            else:
                return False
        finally:
            lock.release()

    def subscribe_table(self, tid):
        self.redis.pubsub(tid)


class BaseHandler(tornado.web.RequestHandler, SessionMixin):

    @property
    def db(self):
        return self.application.db

    @property
    def executor(self):
        return self.application.executor

    @property
    def redis(self):
        return self.application.redis

    def data_received(self, chunk):
        pass

    # def on_finish(self):
    #     self.session.flush()

    def get_current_user(self):
        u_id = self.get_secure_cookie("uid")
        if not u_id:
            return None
        user_id = u_id.decode('utf-8')
        return self.db.account.find_one({'_id': ObjectId(user_id)})


class BaseSocketHandler(tornado.websocket.WebSocketHandler, SessionMixin):

    def on_message(self, message):
        pass

    @property
    def db(self):
        return self.application.db

    @property
    def executor(self):
        return self.application.executor

    @property
    def redis(self):
        return self.application.redis

    def data_received(self, chunk):
        pass

    # def on_finish(self):
    #     self.session.flush()

    @property
    def uid(self):
        u_id = self.get_secure_cookie("uid")
        if not u_id:
            return ''
        return u_id.decode('utf-8')

    def get_current_user(self):
        u_id = self.uid
        if not u_id:
            return None
        return self.db.account.find_one({'_id': ObjectId(u_id)})
