from sqlalchemy import Column, Integer
from sqlalchemy.orm import relationship

from ..base import Base


class DiscordUser(Base):

    __tablename__ = 'discord_users'

    user_id = Column(Integer, primary_key=True)
    reddit_accounts = relationship("RedditUser")

    def __repr__(self):
        return f"<Discord User id='{self.user_id}'>"
