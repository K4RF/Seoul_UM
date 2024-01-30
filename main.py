import discord
from discord.ext import commands
from config import TOKEN
from command import setup_commands
from event_handler import setup_event_handlers

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Setup commands and event handlers
setup_commands(bot)
setup_event_handlers(bot)

# Run the bot
bot.run(TOKEN)
