import discord
from discord import Intents
from discord.ext.commands import Bot
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option
from config import TOKEN, TARGET_WORDS, EXCEPTION_WORDS, TARGET_USERS, TARGET_ROLE_IDS, target_channel_id, ALLOWED_USERS
from data_management import save_data, load_data
from datetime import datetime, timedelta
import asyncio

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = Bot(command_prefix="!", self_bot=True, intents=Intents.default())
slash = SlashCommand(bot)

# 내장된 도움말 명령어 비활성화
bot.remove_command('help')

# 파일에서 데이터 로드
data = load_data()

# 금지된 단어 및 대상 사용자를 저장할 세트
banned_words = set(data.get('banned_words', TARGET_WORDS))
exception_words = set(data.get('exception_words', EXCEPTION_WORDS))
target_users = set(data.get('target_users', TARGET_USERS))
allowed_command_users = set(data.get('allowed_command_users', ALLOWED_USERS))

# 멤버별로 처음 삭제 시간을 저장하는 딕셔너리
first_deletion_time = {}

# 봇의 삭제 기능 활성/비활성 상태를 나타내는 변수
delete_enabled = True

# 로그아웃 및 재시작 여부를 나타내는 변수
logout_done = False
restart_done = False

# 역할 이름을 기반으로 역할을 찾는 함수
def find_role(guild, role_name):
    return discord.utils.get(guild.roles, name=role_name)

# 각 멤버에 대해 첫 번째 오류 메시지가 전송되었는지 여부를 저장하는 딕셔너리
first_error_message_sent = {}

async def send_delayed_message(member, content):
    await asyncio.sleep(60 * 60)  # 60분
    try:
        await member.send(content)
    except discord.errors.Forbidden:
        pass  # DM이 차단되어 있는 경우 무시

@bot.event
async def on_ready():
    global slash
    print(f'{bot.user.name}이(가) 성공적으로 로그인했습니다!')
    target_channel = bot.get_channel(target_channel_id)

    if target_channel:
        await target_channel.send(f'계엄사령부에서 알려드립니다. 계엄령이 선포되었습니다.')
    await slash.sync_all_commands() 

@bot.event
async def on_shutdown():
    # 봇이 종료될 때 메시지를 특정 채널에 보냅니다.
    target_channel = bot.get_channel(target_channel_id)
    if target_channel:
        await target_channel.send(f'계엄령이 해제되었습니다.')

# 메시지에 금지어가 포함되어 있는지 확인하고 처리하는 함수
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

    # 금지어를 확인하고 처리합니다.
    await check_and_handle_banned_words(message, delete_enabled, first_deletion_time, banned_words, exception_words, target_users, TARGET_ROLE_IDS)

    await bot.process_commands(message)

# 메시지 편집 이벤트
@bot.event
async def on_message_edit(before, after):
    global delete_enabled, first_deletion_time, banned_words, exception_words, target_users, TARGET_ROLE_IDS  # 삭제 기능 상태 및 금지어 관련 변수 전역 변수 사용

    # 수정된 메시지가 문자열이 아닌 경우에만 처리합니다.
    if isinstance(after, discord.Message):
        # 금지어를 확인하고 처리합니다.
        await check_and_handle_banned_words(after, delete_enabled, first_deletion_time, banned_words, exception_words, target_users, TARGET_ROLE_IDS)

# setup 함수 호출 후에 Slash 명령어 정의
@slash.slash(name='add_word', description='금지어 목록에 단어 추가', options=[create_option(name='word', description='추가할 단어', option_type=3, required=True)])
async def add_word(ctx: SlashContext, word: str):
    global banned_words
    banned_words.add(word.lower())
    save_data({'banned_words': list(banned_words)})
    await ctx.send(f'이제 님들 "{word}"도 못 씀')

@slash.slash(name='remove_word', description='금지어 목록에서 단어 제거', options=[create_option(name='word', description='제거할 단어', option_type=3, required=True)])
async def remove_word(ctx: SlashContext, word: str):
    global banned_words
    banned_words.discard(word.lower())
    save_data({'banned_words': list(banned_words)})
    await ctx.send(f'"{word}"은(는) 쓰십쇼')

@slash.slash(name='list_words', description='금지어 목록 표시')
async def list_words(ctx: SlashContext):
    await ctx.send(f'금지어 목록: {", ".join(banned_words)}')

@slash.slash(name='add_exception', description='예외 단어 추가', options=[create_option(name='word', description='추가할 예외 단어', option_type=3, required=True)])
async def add_exception(ctx: SlashContext, word: str):
    global exception_words
    exception_words.add(word.lower())
    save_data({'exception_words': list(exception_words)})
    await ctx.send(f'예외 단어 "{word}" 추가해드림')

@slash.slash(name='remove_exception', description='예외 단어 제거', options=[create_option(name='word', description='제거할 예외 단어', option_type=3, required=True)])
async def remove_exception(ctx: SlashContext, word: str):
    global exception_words
    exception_words.discard(word.lower())
    save_data({'exception_words': list(exception_words)})
    await ctx.send(f'"{word}"이것도 이제 예외 아님')

@slash.slash(name='list_exception', description='예외 단어 목록 표시')
async def list_exception(ctx: SlashContext):
    if exception_words:
        await ctx.send(f'예외 단어 목록: {", ".join(exception_words)}')
    else:
        await ctx.send('예외 단어가 없습니다.')

@slash.slash(name='add_user', description='검열 대상 유저 추가', options=[create_option(name='user_id', description='추가할 유저의 ID', option_type=6, required=True)])
async def add_user(ctx: SlashContext, user_id: int):
    # 예외 처리를 추가합니다.
    try:
        member = await ctx.guild.fetch_member(user_id)
        target_users.add(user_id)
        await ctx.send(f'{member.display_name}님이 검열 대상 유저로 추가되었습니다.')
    except discord.NotFound:
        await ctx.send(f'서버 멤버 목록에 {user_id}에 해당하는 사용자가 없습니다.')

@slash.slash(name='remove_user', description='검열 대상 목록에서 유저 제거', options=[create_option(name='user_id', description='제거할 유저 ID', option_type=3, required=True)])
async def remove_user(ctx: SlashContext, user_id: int):
    global target_users
    try:
        target_users.remove(user_id)
        save_data({'target_users': list(target_users)})
        member = ctx.guild.get_member(user_id)
        await ctx.send(f'{member.mention}님 석방임 ㅊㅊ')
        if first_error_message_sent.get(user_id) is None:
            first_error_message_sent[user_id] = True
    except ValueError:
        await ctx.send(f'사용자 {user_id}가 검열 대상 목록에 존재하지 않음')

@slash.slash(name='list_users', description='검열 대상 유저 목록 표시')
async def list_users(ctx: SlashContext):
    # 예외 처리를 추가합니다.
    if target_users:
        user_mentions = [f'<@{user_id}>' for user_id in target_users]
        await ctx.send(f'검열 대상 유저 목록: {", ".join(user_mentions)}')
    else:
        await ctx.send('검열 대상 유저가 없습니다.')

@slash.slash(name='add_allow', description='유저에게 명령어 사용 권한 부여', options=[create_option(name='user_id', description='권한을 부여할 유저 ID', option_type=3, required=True)])
async def add_allow(ctx: SlashContext, user_id: int):
    global allowed_command_users
    member = ctx.guild.get_member(user_id)
    if member:
        allowed_command_users.add(user_id)
        save_data({'allowed_command_users': list(allowed_command_users)})
        user_mention = member.mention
        await ctx.send(f'{user_mention}님 커맨드 쓰십쇼.')
    else:
        await ctx.send(f'서버 멤버 목록에 {user_id}에 해당하는 사용자가 없습니다.')

@slash.slash(name='remove_allow', description='유저의 명령어 사용 권한 해제', options=[create_option(name='user_id', description='권한을 해제할 유저 ID', option_type=3, required=True)])
async def remove_allow(ctx: SlashContext, user_id: int):
    global allowed_command_users
    member = ctx.guild.get_member(user_id)
    if member:
        if user_id in allowed_command_users:
            allowed_command_users.remove(user_id)
            save_data({'allowed_command_users': list(allowed_command_users)})
            user_mention = member.mention
            await ctx.send(f'{user_mention}님 커맨드 권한 해제요.')
        else:
            await ctx.send(f'{user_id}에 해당하는 사용자가 권한 목록에 존재하지 않습니다.')
    else:
        await ctx.send(f'서버 멤버 목록에 {user_id}에 해당하는 사용자가 없습니다.')

@slash.slash(name='list_allowed', description='명령어 사용 권한 부여된 유저 목록 표시')
async def list_allowed(ctx: SlashContext):
    await ctx.send(f'명령어 사용 권한이 부여된 유저 목록: {", ".join(str(user_id) for user_id in allowed_command_users)}')

@slash.slash(name='shutdown', description='봇 종료')
async def shutdown(ctx: SlashContext):
    global delete_enabled, logout_done, restart_done
    delete_enabled = False
    logout_done = True
    restart_done = True
    await ctx.send('계엄령이 해제되었습니다.')
    await bot.close()

@slash.slash(name='logout', description='봇 임시 중단')
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

@slash.slash(name='restart', description='봇 재시작')
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

@slash.slash(name='help', description='사용 가능한 명령어 및 설명 표시')
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
        "`/add_allow [유저ID]`: 유저에게 명령어 사용 권한을 부여합니다.\n"
        "`/remove_allow [유저ID]`: 유저의 명령어 사용 권한을 해제합니다.\n"
        "`/list_allowed`: 명령어 사용 권한이 부여된 유저 목록을 표시합니다.\n"
        "`/shutdown`: 봇을 종료합니다.\n"
        "`/logout`: 봇을 임시 중단합니다.\n"
        "`/restart`: 봇을 재시작합니다.\n"
        "`/help`: 이 메시지를 표시합니다."
    )
    await ctx.send(help_message)

async def main():
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
