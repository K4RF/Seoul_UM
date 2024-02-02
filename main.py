import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option
from config import TOKEN, TARGET_WORDS, EXCEPTION_WORDS, TARGET_USERS, TARGET_ROLE_IDS, target_channel_id, ALLOWED_USERS
from data_management import save_data, load_data
from datetime import datetime, timedelta
import asyncio

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
slash = SlashCommand(bot, sync_commands=True)

# Disable the built-in help command
bot.remove_command('help')

# Load data from file
data = load_data()

# Sets to store banned words and targeted users
banned_words = set(data.get('banned_words', TARGET_WORDS))
exception_words = set(data.get('exception_words', EXCEPTION_WORDS))
target_users = set(data.get('target_users', TARGET_USERS))
allowed_command_users = set(data.get('allowed_command_users', ALLOWED_USERS))

# 멤버별 처음 삭제 시간을 저장할 딕셔너리
first_deletion_time = {}

# 봇의 삭제 기능 활성/비활성 상태를 나타내는 변수
delete_enabled = True

# 로그아웃 및 재시작 여부를 나타내는 변수
logout_done = False
restart_done = False

# 역할 이름을 기반으로 역할을 찾는 함수
def find_role(guild, role_name):
    return discord.utils.get(guild.roles, name=role_name)

# Define a decorator to check if the command invoker is allowed
def is_allowed(ctx):
    return ctx.author.id in allowed_command_users

# Dictionary to store whether the first error message has been sent for each member
first_error_message_sent = {}

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

# Function to check if a message contains banned words and handle it
async def check_and_handle_banned_words(message, delete_enabled, first_deletion_time, banned_words, exception_words, target_users, TARGET_ROLE_IDS):
    if message.author.id in target_users and delete_enabled:
        current_time = datetime.utcnow()

        # 멤버가 처음으로 메시지를 삭제한 시간
        member = message.guild.get_member(message.author.id)
        first_time = first_deletion_time.get(member)

        # 금지어가 포함된 경우만 처리
        for target_word in banned_words:
            if (
                target_word.lower() in message.content.lower()
                or any(role.id in TARGET_ROLE_IDS for role in message.role_mentions)
            ):
                # 예외 단어가 포함된 경우 처리하지 않음
                if any(exception_word.lower() in message.content.lower() for exception_word in exception_words):
                    return

                fetched_message = None
                try:
                    fetched_message = await message.channel.fetch_message(message.id)
                except discord.errors.NotFound:
                    pass  # 메시지가 이미 삭제된 경우 무시
                except discord.errors.HTTPException as e:
                    if e.status == 429:
                        await asyncio.sleep(1)  # Rate Limit이 발생한 경우 1초 대기 후 다시 시도
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
                            await message.channel.send(
                                f'{message.author.mention}, 그 단어 쓰지 말라 했제. '
                                f'이번만 알려준다'
                            )
                        except discord.errors.NotFound:
                            pass  # 채널이 이미 삭제된 경우 무시

                        first_deletion_time[member] = current_time

                        delayed_message = f'{message.author.mention}, 그 단어 쓰지 말라 했제. ' \
                                          f'이번만 알려준다'
                        bot.loop.create_task(send_delayed_message(member, delayed_message))

                return  # 다음 동작을 방지하기 위해 리턴
            
@bot.event
async def on_message(message):
    global delete_enabled, first_deletion_time, banned_words, exception_words, target_users, TARGET_ROLE_IDS  # 삭제 기능 상태 및 금지어 관련 변수 전역 변수 사용

    # Check and handle banned words
    await check_and_handle_banned_words(message, delete_enabled, first_deletion_time, banned_words, exception_words, target_users, TARGET_ROLE_IDS)

    await bot.process_commands(message)

# Message edit event
@bot.event
async def on_message_edit(before, after):
    global delete_enabled, first_deletion_time, banned_words, exception_words, target_users, TARGET_ROLE_IDS  # 삭제 기능 상태 및 금지어 관련 변수 전역 변수 사용

    # Check and handle banned words
    await check_and_handle_banned_words(after, delete_enabled, first_deletion_time, banned_words, exception_words, target_users, TARGET_ROLE_IDS)


@slash.slash(name='add_word', description='Add a word to the banned list', options=[create_option(name='word', description='The word to add', option_type=3, required=True)])
async def add_word(ctx: SlashContext, word: str):
    banned_words.add(word.lower())
    save_data({'banned_words': list(banned_words)})
    await ctx.send(f'이제 님들 "{word}"도 못 씀')

@slash.slash(name='remove_word', description='Remove a word from the banned list', options=[create_option(name='word', description='The word to remove', option_type=3, required=True)])
async def remove_word(ctx: SlashContext, word: str):
    banned_words.discard(word.lower())
    save_data({'banned_words': list(banned_words)})
    await ctx.send(f'"{word}"은 쓰십쇼')

@slash.slash(name='list_words', description='List all banned words')
async def list_words(ctx: SlashContext):
    await ctx.send(f'Banned words: {", ".join(banned_words)}')

@slash.slash(name='add_exception', description='Add an exception word', options=[create_option(name='word', description='The exception word to add', option_type=3, required=True)])
async def add_exception(ctx: SlashContext, word: str):
    exception_words.add(word.lower())
    save_data({'exception_words': list(exception_words)})
    await ctx.send(f'예외 단어 "{word}" 추가해드림')

@slash.slash(name='remove_exception', description='Remove an exception word', options=[create_option(name='word', description='The exception word to remove', option_type=3, required=True)])
async def remove_exception(ctx: SlashContext, word: str):
    exception_words.discard(word.lower())
    save_data({'exception_words': list(exception_words)})
    await ctx.send(f'"{word}"이것도 이제 예외 아님')

@slash.slash(name='list_exception', description='List all exception words')
async def list_exception(ctx: SlashContext):
    await ctx.send(f'Exception words: {", ".join(exception_words)}')

@slash.slash(name='add_user', description='Add a user to the targeted list', options=[create_option(name='user_id', description='The user ID to add', option_type=3, required=True)])
async def add_user(ctx: SlashContext, user_id: int):
    target_users.add(user_id)
    save_data({'target_users': list(target_users)})
    member = ctx.guild.get_member(user_id)
    await ctx.send(f'앞으로 {member.mention}님도 검열 대상임 알아서 하셈')

@slash.slash(name='remove_user', description='Remove a user from the targeted list', options=[create_option(name='user_id', description='The user ID to remove', option_type=3, required=True)])
async def remove_user(ctx: SlashContext, user_id: int):
    try:
        target_users.remove(user_id)
        save_data({'target_users': list(target_users)})
        member = ctx.guild.get_member(user_id)
        await ctx.send(f'{member.mention}님 석방임 ㅊㅊ')
        if first_error_message_sent.get(user_id) is None:
            first_error_message_sent[user_id] = True
    except ValueError:
        await ctx.send(f'사용자 {user_id}가 검열 대상 목록에 존재하지 않음')

@slash.slash(name='list_users', description='List all targeted users')
async def list_users(ctx: SlashContext):
    await ctx.send(f'Targeted users: {", ".join(str(user_id) for user_id in target_users)}')

@slash.slash(name='add_allow', description='Grant command usage permission to a user', options=[create_option(name='user_id', description='The user ID to grant permission', option_type=3, required=True)])
async def add_allow(ctx: SlashContext, user_id: int):
    if user_id is None:
        await ctx.send("유저 ID를 똑바로 붙이라고.")
        return

    member = ctx.guild.get_member(user_id)
    if member:
        allowed_command_users.add(user_id)
        save_data({'allowed_command_users': list(allowed_command_users)})
        user_mention = member.mention
        await ctx.send(f'{user_mention}님 커맨드 쓰십쇼.')
    else:
        await ctx.send(f"해당 서버의 멤버 목록에 {user_id}에 해당하는 사용자가 없습니다.")

@slash.slash(name='remove_allow', description='Revoke command usage permission from a user', options=[create_option(name='user_id', description='The user ID to revoke permission', option_type=3, required=True)])
async def remove_allow(ctx: SlashContext, user_id: int):
    if user_id is None:
        await ctx.send("유저 ID를 똑바로 붙이라고.")
        return

    member = ctx.guild.get_member(user_id)
    if member:
        if user_id in allowed_command_users:
            allowed_command_users.remove(user_id)
            save_data({'allowed_command_users': list(allowed_command_users)})
            user_mention = member.mention
            await ctx.send(f'{user_mention}님 커맨드 권한 해제요 .')
        else:
            await ctx.send(f'{user_id}에 해당하는 사용자가 권한 목록에 존재하지 않습니다.')
    else:
        await ctx.send(f"해당 서버의 멤버 목록에 {user_id}에 해당하는 사용자가 없습니다.")

@slash.slash(name='list_allowed', description='List all users with command usage permission')
async def list_allowed(ctx: SlashContext):
    await ctx.send(f'Allowed command users: {", ".join(str(user_id) for user_id in allowed_command_users)}')

@slash.slash(name='shutdown', description='Shutdown the bot')
async def shutdown(ctx: SlashContext):
    global delete_enabled, logout_done, restart_done
    delete_enabled = False
    logout_done = True
    restart_done = True
    await ctx.send('계엄령이 해제되었습니다.')
    await bot.close()

@slash.slash(name='logout', description='Temporarily stop the bot')
async def logout(ctx: SlashContext):
    global delete_enabled, logout_done, restart_done
    if not logout_done:
        delete_enabled = False
        logout_done = True
        restart_done = False
        await ctx.send('계엄령이 임시 해제되었습니다')
        await bot.change_presence(status=discord.Status.idle)
    else:
        await ctx.send('이미 로그아웃이 수행되었습니다.')

@slash.slash(name='restart', description='Restart the bot')
async def restart(ctx: SlashContext):
    global delete_enabled, logout_done, restart_done
    if not restart_done:
        delete_enabled = True
        restart_done = True
        logout_done = False
        await bot.change_presence(status=discord.Status.online)
        await ctx.send('계엄령을 재선포합니다.')
    else:
        await ctx.send('이미 재시작이 수행되었습니다.')

@slash.slash(name='help', description='Show available commands and their descriptions')
async def help_command(ctx: SlashContext):
    """
    봇의 사용 가능한 명령어와 간단한 설명을 표시합니다.
    """
    help_message = (
        "**명령어 목록**\n"
        "일반 명령어는 `!`를 사용하고, 슬래시 명령어는 `/`를 사용합니다.\n"
        "`/add_word [단어]`: 금지어 목록에 단어를 추가합니다.\n"
        "`/remove_word [단어]`: 금지어 목록에서 단어를 제거합니다.\n"
        "`/list_words`: 금지어 목록을 표시합니다.\n"
        "`/add_exception [단어]`: 예외 단어 목록에 단어를 추가합니다.\n"
        "`/remove_exception [단어]`: 예외 단어 목록에서 단어를 제거합니다.\n"
        "`/list_exception`: 예외 단어 목록을 표시합니다.\n"
        "`/add_user [유저ID]`: 검열 대상 목록에 유저를 추가합니다.\n"
        "`/remove_user [유저ID]`: 검열 대상 목록에서 유저를 제거합니다.\n"
        "`/list_users`: 검열 대상 목록을 표시합니다.\n"
        "`/add_allow [유저ID]`: 커맨드 사용 권한을 부여합니다.\n"
        "`/remove_allow [유저ID]`: 커맨드 사용 권한을 해제합니다.\n"
        "`/list_allowed`: 커맨드 사용 권한이 부여된 유저 목록을 표시합니다.\n"
        "`/shutdown`: 봇을 종료합니다.\n"
        "`/logout`: 봇을 임시 중단합니다.\n"
        "`/restart`: 봇을 재시작합니다."
    )
    await ctx.send(help_message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        # Check if the first error message has been sent for this member
        if first_error_message_sent.get(ctx.author.id) is None:
            # Set the flag to True
            first_error_message_sent[ctx.author.id] = True
            # Send the error message
            await ctx.send("님 권한 없음 ㅅㄱ")
    elif isinstance(error, commands.CommandNotFound):
        # Send the error message for CommandNotFound
        # Check if the first error message has been sent for this member
        if first_error_message_sent.get(ctx.author.id) is None:
            # Set the flag to True
            first_error_message_sent[ctx.author.id] = True
            await ctx.send("님 명령어 잘못 적음")
    else:
        raise error

# 봇을 실행
bot.run(TOKEN)
