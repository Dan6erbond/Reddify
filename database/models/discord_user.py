from sqlalchemy import Column, Integer

from ..base import Base


class DiscordUser(Base):

    __tablename__ = 'discord_users'

    user_id = Column(Integer, primary_key=True)

    def __repr__(self):
        return f"<Discord User id='{self.user_id}'>"
