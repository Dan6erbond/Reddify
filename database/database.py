from sqlalchemy import create_engine
from sqlalchemy.orm import backref, relationship, sessionmaker
import pathlib
from .base import Base
from .models.reddit_user import RedditUser
from .models.discord_user import DiscordUser

path = pathlib.Path(__file__).parent.absolute()
engine = create_engine(f'sqlite:///{path}/database.db')

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()
