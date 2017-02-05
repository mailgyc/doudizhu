import tornado.websocket
from bson import ObjectId


class BaseHandler(tornado.web.RequestHandler):

    @property
    def db(self):
        return self.application.db

    @property
    def executor(self):
        return self.application.executor

    @property
    def session(self):
        return self.application.session

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


class BaseSocketHandler(tornado.websocket.WebSocketHandler):

    def on_message(self, message):
        pass

    @property
    def db(self):
        return self.application.db

    @property
    def executor(self):
        return self.application.executor

    @property
    def session(self):
        return self.application.session

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
