import configparser

import apraw
import discord
from discord.ext import commands

reddit = apraw.Reddit("TRB")

bot = commands.Bot("!", description="The official Reddify bot by Dan6erbond to seamlessly connect Reddit and Discord.")

config = configparser.ConfigParser()
config.read("discord.ini")

cogs_to_load = []


@bot.event
async def on_ready():
    print(f'{bot.user.name} is running.')

if __name__ == "__main__":
    for extension in cogs_to_load:
        bot.load_extension(extension)
        print(f'{extension} loaded.')

    bot.run(config["TRB"]["token"])
