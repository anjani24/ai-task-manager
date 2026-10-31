from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import Uuid

from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    tasks = relationship("Task", back_populates="user")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), default="medium")
    completed = Column(Boolean, default=False)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    user = relationship("User", back_populates="tasks")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False)
    family_id = Column(Uuid(as_uuid=True), nullable=False, index=True)
    replaced_by_id = Column(
        Integer,
        ForeignKey("refresh_tokens.id"),
        nullable=True
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    user = relationship("User")
    replaced_by = relationship(
        "RefreshToken",
        remote_side="RefreshToken.id",
        foreign_keys=[replaced_by_id],
        uselist=False
    )