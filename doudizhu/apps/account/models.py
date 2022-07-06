from datetime import datetime
from sqlalchemy import Column, Integer, String, SmallInteger, TIMESTAMP

from contrib.db.orm import Base


class Account(Base):
    __tablename__ = 'account'
    __table_args__ = {'mysql_collate': 'utf8mb4_general_ci'}
    id = Column(Integer, primary_key=True)
    openid = Column(String(50), unique=True)
    username = Column(String(50))
    sex = Column(SmallInteger)
    avatar = Column(String(256))
    date_joined = Column(TIMESTAMP, default=datetime.now)
    last_modified = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'uid': self.id,
            'username': self.username,
            'sex': self.sex,
            'avatar': self.avatar
        }
