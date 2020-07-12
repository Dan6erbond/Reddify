from sqlalchemy import Boolean, Column, Integer, String

from ..base import Base


class Channel(Base):

    __tablename__ = 'channels'

    channel_id = Column(Integer, primary_key=True)
    subreddit = Column(String(50))

    def __repr__(self):
        return f"<Channel id={self.id}>"
