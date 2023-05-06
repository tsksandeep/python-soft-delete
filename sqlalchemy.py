from sqlalchemy.orm import Session, Query
from sqlalchemy import Column, DateTime, func


def clock_timestamp():
    """Abstracts ORM clock timestamp function"""
    return func.clock_timestamp()


class SoftDeletionQuery(Query):
    def soft_delete(self, *args, **kwargs):
        return self.filter(*args, **kwargs).update(
            values={"deleted_at": clock_timestamp()}, synchronize_session=False
        )


class SoftDeletionSession(Session):
    def query(self, *entities):
        query = SoftDeletionQuery(entities, session=self)

        for entity in entities:
            if hasattr(entity, "deleted_at"):
                query = query.filter(entity.deleted_at == None)

        return query


class SoftDeletionBase:
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set when this object is deleted",
    )


# ----------------------------------------------
#                   Models.py
# ----------------------------------------------

from sqlalchemy import (
    Column,
    DateTime,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class SampleModel(Base, SoftDeletionBase):
    """Sample Model"""

    __tablename__ = "sample_table"
    id = Column(UUID, primary_key=True)
    name = Column(String(255), nullable=False)


# ----------------------------------------------
#                   db.py
# ----------------------------------------------

from sqlalchemy import sql, orm

ENGINE = sql.create_engine("DB_CONN_STRING")
SESSION_FACTORY = orm.sessionmaker(bind=ENGINE, class_=SoftDeletionSession)


class DBHandler:
    """Class for managing database access"""

    def __init__(self):
        """Constructor"""
        self.session = SESSION_FACTORY()
        return self.session


handler = DBHandler()

# Sample soft delete
handler.session.query(SampleModel).soft_delete(id=id)
