from datetime import datetime

from sqlalchemy import Column, Integer, TIMESTAMP
from sqlalchemy.dialects.mysql import Insert
from sqlalchemy.engine import Result, ScalarResult, CursorResult
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import Select

__all__ = ('SessionMixin', 'BaseModel')
Base = declarative_base()
engine = create_async_engine("mysql+aiomysql://root:123456@127.0.0.1:3306/ddz", echo=True)
maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class BaseModel(Base):
    __table_args__ = {'mysql_collate': 'utf8mb4_general_ci'}
    __abstract__ = True
    id = Column(Integer, primary_key=True)
    date_joined = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)
    last_modified = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)


class SessionMixin:

    async def get_one_or_none(self, stmt: Select):
        async with self.session as session:
            async with session.begin():
                result: Result = await session.execute(stmt)
                return result.scalar_one_or_none()

    async def get_all(self, stmt: Select) -> ScalarResult:
        async with self.session as session:
            async with session.begin():
                result: Result = await session.execute(stmt)
                return result.scalars()

    async def insert_or_update(self, insert_stmt: Insert, **kwargs) -> int:
        async with self.session as session:
            async with session.begin():
                on_duplicate_key_stmt = insert_stmt.on_duplicate_key_update(**kwargs)
                result: CursorResult = await session.execute(on_duplicate_key_stmt)
                return result.lastrowid

    @property
    def session(self) -> AsyncSession:
        return maker()
