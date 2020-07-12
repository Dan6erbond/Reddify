import configparser

import apraw
import discord
from discord.ext import commands

from cogs import UserCog

reddit = apraw.Reddit("TRB")

bot = commands.Bot("!", description="The official Reddify bot by Dan6erbond to seamlessly connect Reddit and Discord.")

config = configparser.ConfigParser()
config.read("discord.ini")


@bot.event
async def on_ready():
    print(f'{bot.user.name} is running.')

if __name__ == "__main__":
    bot.add_cog(UserCog(bot, reddit))
    bot.run(config["TRB"]["token"])
