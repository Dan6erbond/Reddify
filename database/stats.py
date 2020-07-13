from sqlalchemy import desc, func
from sqlalchemy.sql.expression import false, true

from .database import session
from .models import DiscordUser, RedditUser, Guild

print("Loading stats for Reddify database...")
print("")

verified_users = session.query(RedditUser).filter(RedditUser.verified == true()).all()
print(f"Number of verified Reddit users: {len(verified_users)}")

unverified_users = session.query(RedditUser).filter(RedditUser.verified == false()).all()
print(f"Number of unverified Reddit users: {len(unverified_users)}")

print("")

discord_users = session.query(DiscordUser).all()
print(f"Discord users known to Reddify: {len(discord_users)}")

print("")

most_used = session.query(RedditUser, func.count(RedditUser.discord_user).label('qty')).group_by(
    RedditUser.discord_user).order_by(desc('qty')).first()
print(f"Reddit user with most connected accounts: /u/{most_used[0].username}")
print(f"Number of connected accounts: {len(most_used[0].discord_account.reddit_accounts)}")

print("")

guilds = session.query(Guild).all()
print(f"Guilds using Reddify: {len(guilds)}")
