from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.schema import ForeignKey

from ..base import Base


class RedditUser(Base):

    __tablename__ = 'reddit_users'

    user_id = Column(String(10), primary_key=True)
    discord_user = Column(Integer, ForeignKey("discord_users.user_id"), nullable=False)
    username = Column(String(50), unique=True)
    verified = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Reddit User id={self.id} username={self.username}>"
