import time

import apraw
from discord.ext import commands
from sqlalchemy import func

from const import MAINTAINER, EMOJIS
from database.database import session
from database.models import DiscordUser, RedditUser


class UserCog(commands.Cog):
    def __init__(self, bot: commands.Bot, reddit: apraw.Reddit):
        self.bot = bot
        self.reddit = reddit

    @commands.command(help="Sends a PM to the Reddit user to await confirmation of the account ownership.")
    async def verify(self, ctx: commands.Context, user: str):
        user = user.replace("u/", "").replace("/", "").strip().lower()

        for reddit_user in session.query(RedditUser).filter(RedditUser.discord_user == ctx.author.id):
            if not reddit_user.verified:
                await ctx.message.channel.send(
                    f"❗ /u/{reddit_user.username} is still awaiting verification on Reddit. " +
                    f"If you would like to unlink it, use `!unverify {reddit_user.username}`.")
                return
            else:
                await ctx.message.channel.send(f"❗ /u/{user} is already linked to your Discord account!")
                return

        for reddit_user in session.query(RedditUser).filter(func.lower(RedditUser.username) == user):
            if reddit_user.discord_user != ctx.author.id:
                await ctx.message.channel.send(
                    f"❗ /u/{user} is already linked to another Discord account! " +
                    f"If you believe this is an error, please contact {MAINTAINER}.")
                return

        try:
            redditor = await self.reddit.redditor(user)
        except Exception as e:
            await ctx.message.channel.send(f"❌ Redditor /u/{user} doesn't exist!\n\nError:{e}")
        else:
            await redditor.message("Account Ownership Confirmation",
                                   f"Please reply to this message with 'verify' to confirm that you are Discord user '{ctx.message.author}'.")
            msg = await ctx.message.channel.send(
                f"Check your Reddit PMs to verify you are the owner of /u/{redditor.name} by responding with `verify`!")

            reddit_user = RedditUser(user_id=redditor.fullname, discord_user=ctx.author.id, username=redditor.name)
            session.add(reddit_user)

            time_started = time.time()
            auth_user = await self.reddit.user.me()
            async for message in auth_user.unread.stream(skip_existing=True):
                if not isinstance(message, apraw.models.Message):
                    continue
                if not "Account Ownership Confirmation" in message.subject:
                    continue

                author = await message.author()
                if author.name.lower() != reddit_user.username.lower():
                    continue

                if "verify" in message.body.lower() and not "unverify" in message.body.lower():
                    reddit_user.verified = True
                    user = self.bot.get_user(reddit_user.discord_user)
                    if user is not None:
                        await msg.add_reaction(EMOJIS["CHECK"])
                        await message.reply(f"Confirmation of {user} successful!")
                else:
                    message.reply(
                        "Discord user unlinked from your Reddit account. " +
                        "Please run `!verify` again if this is an error and respond to the new PM.")
                    session.delete(reddit_user)

                break

            session.commit()

    @commands.command(help="Unlink a Reddit account from your Discord handle.")
    async def unverify(self, ctx: commands.Context, user: str):
        for reddit_user in session.query(RedditUser).filter(func.lower(RedditUser.username) == user):
            if reddit_user.discord_user != ctx.author.id:
                await ctx.channel.send(f"<{EMOJIS['XMARK']}> /u/{user} isn't linked to your account!")
                return
            else:
                session.delete(reddit_user)
                session.commit()
                await ctx.channel.send(f"<{EMOJIS['CHECK']}> Successfully unlinked /u/{user}!")
