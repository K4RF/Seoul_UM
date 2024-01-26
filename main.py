import discord
import asyncio
from discord.ext import commands
from config import TOKEN, TARGET_USERS, TARGET_WORDS
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 사용자별 처음 삭제 시간을 저장할 딕셔너리
first_deletion_time = {}

@bot.event
async def on_ready():
    print(f'{bot.user.name}이(가) 성공적으로 로그인했습니다!')

async def send_delayed_message(author, content):
    await asyncio.sleep(60 * 60)  # 60분
    try:
        await author.send(content)
    except discord.errors.Forbidden:
        pass  # DM이 차단되어 있는 경우 무시

@bot.event
async def on_message(message):
    if message.author.id in TARGET_USERS:
        current_time = datetime.utcnow()

        # 사용자가 처음으로 메시지를 삭제한 시간
        first_time = first_deletion_time.get(message.author.id)

        # 금지어가 포함된 경우만 처리
        for target_word in TARGET_WORDS:
            if target_word.lower() in message.content.lower():
                try:
                    await message.delete()
                except discord.errors.NotFound:
                    pass  # 메시지가 이미 삭제된 경우 무시

                if first_time is None:
                    try:
                        await message.channel.send(f'{message.author.mention}, 메시지에 포함된 단어로 인해 메시지가 삭제되었습니다. '
                                                   f'최초 삭제 시에만 봇이 이 메시지를 보냅니다.')
                    except discord.errors.NotFound:
                        pass  # 채널이 이미 삭제된 경우 무시

                    # 현재 시간으로 업데이트
                    first_deletion_time[message.author.id] = current_time

                    # 최초 삭제 시에만 사용자에게 다시 메시지 보내기
                    delayed_message = f'{message.author.mention}, 이 메시지는 금지어가 포함되어 삭제되었습니다. ' \
                                      f'최초 삭제 시에만 봇이 이 메시지를 보냅니다.'
                    bot.loop.create_task(send_delayed_message(message.author, delayed_message))

                return  # 다음 동작을 방지하기 위해 리턴

    await bot.process_commands(message)

bot.run(TOKEN)
