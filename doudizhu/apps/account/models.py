from sqlalchemy import Column, String, SmallInteger

from contrib.db.orm import BaseModel


class Account(BaseModel):
    __tablename__ = 'account'
    openid = Column(String(50), unique=True)
    username = Column(String(50))
    sex = Column(SmallInteger)
    avatar = Column(String(256))

    def to_dict(self):
        return {
            'uid': self.id,
            'username': self.username,
            'sex': self.sex,
            'avatar': self.avatar
        }
