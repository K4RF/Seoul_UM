import discord
from discord.ext import commands
from config import TOKEN, TARGET_WORDS, EXCEPTION_WORDS, TARGET_USERS, target_channel_id
from datetime import datetime, timedelta
import asyncio

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Sets to store banned words and targeted users
banned_words = set(TARGET_WORDS)
exception_words = set(EXCEPTION_WORDS)
target_users = set(TARGET_USERS)

# 멤버별 처음 삭제 시간을 저장할 딕셔너리
first_deletion_time = {}

@bot.event
async def on_ready():
    print(f'{bot.user.name}이(가) 성공적으로 로그인했습니다!')

    # 봇이 켜질 때 메시지를 특정 채널에 보냅니다.
    target_channel = bot.get_channel(target_channel_id)
    if target_channel:
        await target_channel.send(f'계엄사령부에서 알려드립니다. 계엄령이 선포되었습니다!')

async def send_delayed_message(member, content):
    await asyncio.sleep(60 * 60)  # 60분
    try:
        await member.send(content)
    except discord.errors.Forbidden:
        pass  # DM이 차단되어 있는 경우 무시

@bot.event
async def on_shutdown():
    # 봇이 종료될 때 메시지를 특정 채널에 보냅니다.
    target_channel = bot.get_channel(target_channel_id)
    if target_channel:
        await target_channel.send(f'계엄령이 해제되었습니다.')

@bot.event
async def on_message(message):
    if message.author.id in target_users:
        current_time = datetime.utcnow()

        # 멤버가 처음으로 메시지를 삭제한 시간
        member = message.guild.get_member(message.author.id)
        first_time = first_deletion_time.get(member)

        # 금지어가 포함된 경우만 처리
        for target_word in banned_words:
            if target_word.lower() in message.content.lower():
                # 예외 단어가 포함된 경우 처리하지 않음
                if any(exception_word.lower() in message.content.lower() for exception_word in exception_words):
                    return

                fetched_message = None  # Initialize to None outside the try block
                try:
                    # 메시지가 존재하는지 확인 후 삭제 시도
                    fetched_message = await message.channel.fetch_message(message.id)
                except discord.errors.NotFound:
                    pass  # 메시지가 이미 삭제된 경우 무시
                except discord.errors.HTTPException as e:
                    if e.status == 429:
                        # Rate Limit이 발생한 경우, 5초 대기 후 다시 시도
                        await asyncio.sleep(5)
                        try:
                            fetched_message = await message.channel.fetch_message(message.id)
                        except discord.errors.NotFound:
                            pass  # 메시지가 이미 삭제된 경우 무시

                if fetched_message:
                    try:
                        await fetched_message.delete()
                    except discord.errors.NotFound:
                        pass  # 메시지가 이미 삭제된 경우 무시

                    if first_time is None:
                        try:
                            await message.channel.send(f'{message.author.mention}, 메시지에 그 단어가 포함돼 메시지가 삭제되었습니다. '
                                                       f'최초 삭제 시에만 봇이 이 메시지를 보냅니다.')
                        except discord.errors.NotFound:
                            pass  # 채널이 이미 삭제된 경우 무시

                        # 현재 시간으로 업데이트
                        first_deletion_time[member] = current_time

                        # 최초 삭제 시에만 멤버에게 다시 메시지 보내기
                        delayed_message = f'{message.author.mention}, 이 메시지는 그 단어가 포함되어 삭제되었습니다. ' \
                                          f'최초 삭제 시에만 봇이 이 메시지를 보냅니다.'
                        bot.loop.create_task(send_delayed_message(member, delayed_message))

                return  # 다음 동작을 방지하기 위해 리턴

    await bot.process_commands(message)

@bot.command(name='add_banned_word')
async def add_banned_word(ctx, word):
    banned_words.add(word.lower())
    await ctx.send(f'The word "{word}" has been added to the list of banned words.')

@bot.command(name='remove_banned_word')
async def remove_banned_word(ctx, word):
    banned_words.discard(word.lower())
    await ctx.send(f'The word "{word}" has been removed from the list of banned words.')

@bot.command(name='list_banned_words')
async def list_banned_words(ctx):
    await ctx.send(f'Banned words: {", ".join(banned_words)}')

@bot.command(name='add_exception_word')
async def add_exception_word(ctx, word):
    exception_words.add(word.lower())
    await ctx.send(f'The exception word "{word}" has been added.')

@bot.command(name='remove_exception_word')
async def remove_exception_word(ctx, word):
    exception_words.discard(word.lower())
    await ctx.send(f'The exception word "{word}" has been removed.')

@bot.command(name='list_exception_words')
async def list_exception_words(ctx):
    await ctx.send(f'Exception words: {", ".join(exception_words)}')

@bot.command(name='add_target_user')
async def add_target_user(ctx, user_id: int):
    target_users.add(user_id)
    await ctx.send(f'The user with ID {user_id} has been added to the list of targeted users.')

@bot.command(name='remove_target_user')
async def remove_target_user(ctx, user_id: int):
    target_users.discard(user_id)
    await ctx.send(f'The user with ID {user_id} has been removed from the list of targeted users.')

@bot.command(name='list_target_users')
async def list_target_users(ctx):
    await ctx.send(f'Targeted users: {", ".join(str(user_id) for user_id in target_users)}')

bot.run(TOKEN)
