# bot.py
import discord
from discord.ext import commands
from config import TOKEN
from event_handler import setup_event_handlers
from command import setup_commands

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

def run_bot():
    setup_commands(bot)
    setup_event_handlers(bot)
    bot.run(TOKEN)
