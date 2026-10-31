from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from backend.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


def make_database(url: str):
    engine = create_engine(url, connect_args={'check_same_thread': False})
    return engine, sessionmaker(engine, expire_on_commit=False)


engine, SessionLocal = make_database(DATABASE_URL)
