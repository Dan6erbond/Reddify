import json
import pathlib

import praw
from sqlalchemy.sql.expression import or_

from .database import session
from .models import Channel, DiscordUser, Guild, RedditUser

path = pathlib.Path(__file__).parent.absolute()
reddit = praw.Reddit("TRB")


def main():
    with open(f'{path}/database-old/channels.json') as f:
        channels = json.loads(f.read())
        for c in channels:
            subreddit = c["subreddit"] if "subreddit" in c else None

            if channel := session.query(Channel).filter(Channel.channel_id == c["id"]).first():
                channel.subreddit = subreddit
            else:
                channel = Channel(channel_id=c["id"], subreddit=subreddit)
                session.add(channel)

    with open(f'{path}/database-old/guilds.json') as f:
        guilds = json.loads(f.read())
        for g in guilds:
            role = g["role"] if "role" in g else None
            subreddit = g["subreddit"] if "subreddit" in g else None
            set_role = g["set_role"] if "set_role" in g else True
            set_username = g["set_username"] if "set_username" in g else False
            custom_nick = g["custom_nick"] if "custom_nick" in g else False

            if guild := session.query(Guild).filter(Guild.guild_id == g["id"]).first():
                guild.role = role
                guild.subreddit = subreddit
                guild.set_role = set_role
                guild.set_username = set_username
                guild.custom_nick = custom_nick
            else:
                guild = Guild(
                    guild_id=g["id"],
                    subreddit=subreddit,
                    role=role,
                    set_role=set_role,
                    set_username=set_username,
                    custom_nick=custom_nick)
                session.add(guild)

    with open(f'{path}/database-old/users.json') as f:
        users = json.loads(f.read())
        for u in users:
            if not session.query(DiscordUser).filter(DiscordUser.user_id == u["discord"]).first:
                discord_user = DiscordUser(user_id=u["discord"])
                session.add(discord_user)
            for acc in u["verified-reddits"]:
                redditor = reddit.redditor(acc)
                try:
                    user_id = f"t2_{redditor.id}"
                except Exception as e:
                    print(f"Couldn't fetch Redditor {acc}: {e}")
                    continue
                if reddit_user := session.query(RedditUser).filter(
                        or_(RedditUser.username == acc, RedditUser.user_id == user_id)).first():
                    reddit_user.discord_user = u["discord"]
                    reddit_user.verified = True
                    reddit_user.user_id = user_id
                    reddit_user.username = acc
                else:
                    reddit_user = RedditUser(
                        discord_user=u["discord"],
                        user_id=user_id,
                        username=acc,
                        verified=True)
                    session.add(reddit_user)
            if u["unverified-reddit"] and u["unverified-reddit"].lower() not in [acc.lower()
                                                                                 for acc in u["verified-reddits"]]:
                redditor = reddit.redditor(u["unverified-reddit"])
                try:
                    user_id = f"t2_{redditor.id}"
                except Exception as e:
                    print(f"Couldn't fetch Redditor {acc}: {e}")
                    continue
                if reddit_user := session.query(RedditUser).filter(
                        or_(RedditUser.username == acc, RedditUser.user_id == user_id)).first():
                    reddit_user.verified = False
                    reddit_user.user_id = user_id
                else:
                    reddit_user = RedditUser(
                        discord_user=u["discord"],
                        user_id=user_id,
                        username=u["unverified-reddit"],
                        verified=False)
                    session.add(reddit_user)

    session.commit()


if __name__ == "__main__":
    main()
