import discord
from discord.ext import commands
from config import TOKEN, TARGET_USERS, TARGET_WORDS
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 사용자별 마지막 삭제 시간을 저장할 딕셔너리
last_deletion_time = {}

@bot.event
async def on_ready():
    print(f'{bot.user.name}이(가) 성공적으로 로그인했습니다!')

@bot.event
async def on_message(message):
    if message.author.id in TARGET_USERS:
        current_time = datetime.utcnow()

        # 사용자가 마지막으로 메시지를 삭제한 시간
        last_time = last_deletion_time.get(message.author.id)

        # 금지어가 포함된 경우 항상 삭제
        for target_word in TARGET_WORDS:
            if target_word.lower() in message.content.lower():
                await message.delete()
                await message.channel.send(f'{message.author.mention}, 메시지에 포함된 단어로 인해 메시지가 삭제되었습니다.')
                
                # 현재 시간으로 업데이트
                last_deletion_time[message.author.id] = current_time
                return  # 메시지에 금지어가 포함되었을 경우 뒤의 코드 실행하지 않도록

        # 멘션된 사용자 목록 확인
        mentioned_users = [mention.id for mention in message.mentions]
        if any(user_id in TARGET_USERS for user_id in mentioned_users):
            if last_time is None or (current_time - last_time) > timedelta(minutes=5):
                await message.delete()
                await message.channel.send(f'{message.author.mention}, 멘션된 사용자가 금지어를 포함한 메시지를 보냈습니다.')
                
                # 현재 시간으로 업데이트
                last_deletion_time[message.author.id] = current_time

        # 사용자 이름에 금지어가 포함된 경우
        if any(target_word.lower() in message.author.name.lower() for target_word in TARGET_WORDS):
            if last_time is None or (current_time - last_time) > timedelta(minutes=5):
                await message.delete()
                await message.channel.send(f'{message.author.mention}, 사용자 이름에 금지어가 포함된 메시지를 보냈습니다.')
                
                # 현재 시간으로 업데이트
                last_deletion_time[message.author.id] = current_time

    await bot.process_commands(message)

bot.run(TOKEN)
