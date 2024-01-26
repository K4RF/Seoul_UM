import discord
from discord.ext import commands
from config import TOKEN, TARGET_USERS, TARGET_WORDS
import asyncio

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 특정 채널 ID
target_channel_id = 1163856267756970124  # 실제 채널 ID로 변경해야 합니다.

# 멤버별 보낸 횟수를 저장할 딕셔너리
sent_count_data = {}

@bot.event
async def on_ready():
    print(f'{bot.user.name}이(가) 성공적으로 로그인했습니다!')
    
    # 봇이 켜질 때 메시지를 특정 채널에 보냅니다.
    target_channel = bot.get_channel(target_channel_id)
    if target_channel:
        await target_channel.send(f'계엄사령부에서 알려드립니다. 계엄령이 선포되었습니다')

@bot.event
async def on_disconnect():
    # 봇이 꺼질 때 메시지를 특정 채널에 보냅니다.
    target_channel = bot.get_channel(target_channel_id)
    if target_channel:
        await target_channel.send(f'계엄령이 해제되었습니다.')

@bot.event
async def on_message_delete(message):
    # 봇이 보낸 삭제 메시지가 삭제될 때 해당 멤버에게 한 번만 메시지를 보냄
    member = message.guild.get_member(message.author.id)
    if member and member not in sent_count_data:
        try:
            await message.channel.send(f'{message.author.mention}, 봇이 삭제한 메시지를 확인해주세요.')
        except discord.errors.NotFound:
            pass  # 채널이 이미 삭제된 경우 무시

        # 보낸 횟수를 업데이트
        sent_count_data[member] = 1

bot.run(TOKEN)
