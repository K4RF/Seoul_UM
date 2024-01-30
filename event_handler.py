import discord
from discord.ext import commands
from datetime import datetime
import asyncio
from data_management import save_data, load_data
from config import TOKEN, TARGET_WORDS, EXCEPTION_WORDS, TARGET_USERS, TARGET_ROLE_IDS, target_channel_id, ALLOWED_USERS, save_data, load_data

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

async def setup_event_handlers(bot):
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
        global delete_enabled  # 삭제 기능 활성/비활성 상태 전역 변수 사용

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

                    fetched_message = None  # Initialize to None outside the try block
                    try:
                        # 메시지가 존재하는지 확인 후 삭제 시도
                        fetched_message = await message.channel.fetch_message(message.id)
                    except discord.errors.NotFound:
                        pass  # 메시지가 이미 삭제된 경우 무시
                    except discord.errors.HTTPException as e:
                        if e.status == 429:
                            # Rate Limit이 발생한 경우, 1초 대기 후 다시 시도
                            await asyncio.sleep(1)  # 1초
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

                            # 현재 시간으로 업데이트
                            first_deletion_time[member] = current_time

                            # 최초 삭제 시에만 멤버에게 다시 메시지 보내기
                            delayed_message = f'{message.author.mention}, 그 단어 쓰지 말라 했제. ' \
                                            f'이번만 알려준다'
                            bot.loop.create_task(send_delayed_message(member, delayed_message))

                    return  # 다음 동작을 방지하기 위해 리턴

        await bot.process_commands(message)

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
            await ctx.send("님 명령어 잘못 적음")
            # Check if the first error message has been sent for this member
        else:
            raise error
