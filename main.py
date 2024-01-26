import discord
from discord.ext import commands
from config import TOKEN, TARGET_USERS, TARGET_WORDS

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user.name}이(가) 성공적으로 로그인했습니다!')

@bot.event
async def on_message(message):
    if message.author.id in TARGET_USERS:
        for target_word in TARGET_WORDS:
            if target_word.lower() in message.content.lower():
                await message.delete()
                await message.channel.send(f'{message.author.mention}, 메시지에 포함된 단어로 인해 메시지가 삭제되었습니다.')
                break  # 한 번의 메시지에 대해 한 번만 삭제하도록 하기 위해

    await bot.process_commands(message)

bot.run(TOKEN)
