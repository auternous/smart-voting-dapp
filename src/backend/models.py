from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    JSON,
    Text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime, timezone

Base = declarative_base()

# 👤 Пользователь (user = wallet)
class User(Base):
    __tablename__ = "users"

    address = Column(String(42), primary_key=True)
    balance = Column(Integer, default=0)  # можно использовать как динамический кэш
    polls_created = Column(Integer, default=0)
    votes_cast = Column(Integer, default=0)
    balance = Column(Integer, default=0)

    votes = relationship("Vote", back_populates="user")
    polls = relationship("Poll", back_populates="author")

# 📋 Опрос
class Poll(Base):
    __tablename__ = "polls"

    id = Column(Integer, primary_key=True)
    question = Column(Text)
    options = Column(JSON)
    end_time = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    creator_address = Column(String(42), ForeignKey("users.address"))
    author = relationship("User", back_populates="polls")
    votes = relationship("Vote", back_populates="poll")

# 🗳 Голос
class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey("polls.id"))
    user_address = Column(String(42), ForeignKey("users.address"))
    option_id = Column(Integer)
    tx_hash = Column(String(66))
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="votes")
    poll = relationship("Poll", back_populates="votes")

# 🎯 DB init
engine = create_engine("sqlite:///votes.db")
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)