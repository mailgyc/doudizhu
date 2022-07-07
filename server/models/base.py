from sqlalchemy.dialects.mysql import Insert
from sqlalchemy.engine import Result, ScalarResult, CursorResult
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import Select

__all__ = ('AlchemyMixin', 'Base')

from config import DATABASE_URI

Base = declarative_base()
engine = create_async_engine(DATABASE_URI, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class AlchemyMixin:
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

    async def insert(self, instance):
        async with self.session as session:
            async with session.begin():
                session.add(instance)
                await session.commit()

    async def insert_or_update(self, insert_stmt: Insert, **kwargs) -> int:
        async with self.session as session:
            async with session.begin():
                on_duplicate_key_stmt = insert_stmt.on_duplicate_key_update(**kwargs)
                result: CursorResult = await session.execute(on_duplicate_key_stmt)
                return result.lastrowid

    @property
    def session(self) -> AsyncSession:
        return async_session()
