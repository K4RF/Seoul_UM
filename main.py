import discord
from discord.ext import commands
from config import TOKEN, TARGET_USERS, TARGET_WORDS
from datetime import datetime, timedelta
import asyncio

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 멤버별 보낸 횟수를 저장할 딕셔너리
sent_count_data = {}

@bot.event
async def on_ready():
    print(f'{bot.user.name}이(가) 성공적으로 로그인했습니다!')

async def send_delayed_message(member, content):
    await asyncio.sleep(60 * 60)  # 60분
    try:
        await member.send(content)
    except discord.errors.Forbidden:
        pass  # DM이 차단되어 있는 경우 무시

@bot.event
async def on_message_delete(message):
    # 봇이 보낸 삭제 메시지가 삭제될 때 해당 멤버에게 한 번만 메시지를 보냄
    member = message.guild.get_member(message.author.id)
    if member and member not in sent_count_data:
        try:
            await message.channel.send(f'{message.author.mention}, 봇이 삭제한 메시지를 확인해주세요. '
                                       f'이 메시지는 최초 삭제 시에만 봇이 보냅니다.')
        except discord.errors.NotFound:
            pass  # 채널이 이미 삭제된 경우 무시

        # 보낸 횟수를 업데이트
        sent_count_data[member] = 1

        # 최초 삭제 시에만 멤버에게 다시 메시지 보내기
        delayed_message = f'{message.author.mention}, 봇이 삭제한 메시지를 확인해주세요. ' \
                          f'이 메시지는 최초 삭제 시에만 봇이 보냅니다.'
        bot.loop.create_task(send_delayed_message(member, delayed_message))

bot.run(TOKEN)
