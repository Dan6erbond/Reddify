from sqlalchemy import Boolean, Column, Integer, String

from ..base import Base


class Guild(Base):

    __tablename__ = 'guilds'

    guild_id = Column(Integer, primary_key=True)
    role = Column(Integer)
    subreddit = Column(String(50))
    set_role = Column(Boolean, default=False)
    set_username = Column(Boolean, default=False)
    custom_nick = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Guild id='{self.guild_id}' role='{self.role}'>"
