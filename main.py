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

# 멤버별 최초 삭제 시간 및 보낸 여부를 저장할 딕셔너리
first_deletion_data = {}

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
async def on_message(message):
    if message.author.id in TARGET_USERS:
        current_time = datetime.utcnow()

        # 멤버의 최초 삭제 시간 및 보낸 여부
        member = message.guild.get_member(message.author.id)
        deletion_data = first_deletion_data.get(member, {'time': None, 'sent': False})

        # 금지어가 포함된 경우만 처리
        for target_word in TARGET_WORDS:
            if target_word.lower() in message.content.lower():
                try:
                    # 메시지가 존재하는지 확인 후 삭제 시도
                    fetched_message = await message.channel.fetch_message(message.id)
                    await fetched_message.delete()
                except discord.errors.NotFound:
                    pass  # 메시지가 이미 삭제된 경우 무시
                except discord.errors.HTTPException as e:
                    if e.status == 429:
                        # Rate Limit이 발생한 경우, 5초 대기 후 다시 시도
                        await asyncio.sleep(5)
                        try:
                            await fetched_message.delete()
                        except discord.errors.NotFound:
                            pass  # 메시지가 이미 삭제된 경우 무시

                if deletion_data['time'] is None:
                    try:
                        await message.channel.send(f'{message.author.mention}, 메시지에 포함된 단어로 인해 메시지가 삭제되었습니다. '
                                                   f'최초 삭제 시에만 봇이 이 메시지를 보냅니다.')
                    except discord.errors.NotFound:
                        pass  # 채널이 이미 삭제된 경우 무시

                    # 현재 시간으로 업데이트 및 보낸 여부 표시
                    first_deletion_data[member] = {'time': current_time, 'sent': True}

                    # 최초 삭제 시에만 멤버에게 다시 메시지 보내기
                    delayed_message = f'{message.author.mention}, 이 메시지는 금지어가 포함되어 삭제되었습니다. ' \
                                      f'최초 삭제 시에만 봇이 이 메시지를 보냅니다.'
                    bot.loop.create_task(send_delayed_message(member, delayed_message))

                return  # 다음 동작을 방지하기 위해 리턴

    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    # 지연 삭제 중에 봇이 보낸 삭제 메시지가 삭제되면 해당 멤버의 정보를 초기화
    member = message.guild.get_member(message.author.id)
    if member and member in first_deletion_data:
        del first_deletion_data[member]

bot.run(TOKEN)
