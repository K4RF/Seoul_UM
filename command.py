import discord
from discord.ext import commands
from data_management import save_data, load_data
from event_handler import setup_event_handlers  # Correct import
from config import TOKEN, TARGET_WORDS, EXCEPTION_WORDS, TARGET_USERS, TARGET_ROLE_IDS, target_channel_id, ALLOWED_USERS, save_data, load_data
data = load_data()

# Sets to store banned words and targeted users
banned_words = set(data.get('banned_words', TARGET_WORDS))
exception_words = set(data.get('exception_words', EXCEPTION_WORDS))
target_users = set(data.get('target_users', TARGET_USERS))
allowed_command_users = set(data.get('allowed_command_users', ALLOWED_USERS))

# 멤버별 처음 삭제 시간을 저장할 딕셔너리
first_deletion_time = {}

# Define a decorator to check if the command invoker is allowed
def is_allowed(ctx):
    return ctx.author.id in allowed_command_users

# Dictionary to store whether the first error message has been sent for each member
first_error_message_sent = {}

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='add_word')
    @commands.check(is_allowed)  # Check if the invoker is allowed
    async def add_word(self, ctx, word):
        banned_words.add(word.lower())
        save_data({'banned_words': list(banned_words)})
        await ctx.send(f'이제 님들 "{word}"도 못 씀')

    @commands.command(name='remove_word')
    @commands.check(is_allowed)  # Check if the invoker is allowed
    async def remove_word(self, ctx, word):
        banned_words.discard(word.lower())
        save_data({'banned_words': list(banned_words)})
        await ctx.send(f'"{word}"은 쓰십쇼')
    
    @commands.command(name='list_words')
    @commands.check(is_allowed)  # Check if the invoker is allowed
    async def list_words(self, ctx):
        await ctx.send(f'Banned words: {", ".join(banned_words)}')

    @commands.command(name='add_exception')
    @commands.check(is_allowed)  # Check if the invoker is allowed
    async def add_exception(self, ctx, word):
        exception_words.add(word.lower())
        save_data({'exception_words': list(exception_words)})
        await ctx.send(f'예외 단어 "{word}" 추가해드림')

    @commands.command(name='remove_exception')
    @commands.check(is_allowed)  # Check if the invoker is allowed
    async def remove_exception(self, ctx, word):
        exception_words.discard(word.lower())
        save_data({'exception_words': list(exception_words)})
        await ctx.send(f'"{word}"이것도 이제 예외 아님')

    @commands.command(name='list_exception')
    @commands.check(is_allowed)  # Check if the invoker is allowed
    async def list_exception(self, ctx):
        await ctx.send(f'Exception words: {", ".join(exception_words)}')

    @commands.Bot.command(name='add_user')
    @commands.check(is_allowed)  # Check if the invoker is allowed
    async def add_user(ctx, user_id: int):
        target_users.add(user_id)
        save_data({'target_users': list(target_users)})
        member = ctx.guild.get_member(user_id)
        await ctx.send(f'앞으로 {member.mention}님도 검열 대상임 알아서 하셈')

    @commands.Bot.command(name='remove_user')
    @commands.check(is_allowed)  # Check if the invoker is allowed
    async def remove_user(ctx, user_id: int):
        try:
            target_users.remove(user_id)
            save_data({'target_users': list(target_users)})
            member = ctx.guild.get_member(user_id)
            await ctx.send(f'{member.mention}님 석방임 ㅊㅊ')
            # Check if the first error message has been sent for this member
            if first_error_message_sent.get(user_id) is None:
                # Set the flag to True
                first_error_message_sent[user_id] = True
        except ValueError:
            await ctx.send(f'사용자 {user_id}가 검열 대상 목록에 존재하지 않음')

    @commands.Bot.command(name='list_users')
    @commands.check(is_allowed)  # Check if the invoker is allowed
    async def list_users(ctx):
        await ctx.send(f'Targeted users: {", ".join(str(user_id) for user_id in target_users)}')

    @commands.Bot.command(name='add_allow')
    @commands.check(is_allowed)  # Check if the invoker is allowed
    async def add_allow(ctx, user_id: int = None):
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

    @commands.Bot.command(name='remove_allow')
    @commands.check(is_allowed)  # Check if the invoker is allowed
    async def remove_allow(ctx, user_id: int = None):
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

    @commands.Bot.command(name='list_allowed')
    @commands.check(is_allowed)  # Check if the invoker is allowed
    async def list_allowed(ctx):
        await ctx.send(f'Allowed command users: {", ".join(str(user_id) for user_id in allowed_command_users)}')

    @commands.command(name='shutdown')
    @commands.check(is_allowed)  # Check if the invoker is allowed to use commands
    async def shutdown(self, ctx):
        global delete_enabled, logout_done, restart_done  # 삭제 기능 및 상태 변수 전역 변수 사용
        delete_enabled = False  # 봇 종료 시 삭제 기능 비활성화
        logout_done = True  # 로그아웃이 수행됨을 표시
        restart_done = True
        await ctx.send('계엄령이 해제되었습니다.')
        await self.bot.close()

    @commands.command(name='logout')
    @commands.check(is_allowed)  # Check if the invoker is allowed to use commands
    async def logout(self, ctx):
        global delete_enabled, logout_done, restart_done  # 삭제 기능 및 상태 변수 전역 변수 사용
        if not logout_done:
            delete_enabled = False  # 로그아웃 시 삭제 기능 비활성화
            logout_done = True  # 로그아웃이 수행됨을 표시
            restart_done = False
            await ctx.send('계엄령이 임시 해제되었습니다')
            await self.bot.change_presence(status=discord.Status.idle)
        else:
            await ctx.send('이미 로그아웃이 수행되었습니다.')

    @commands.command(name='restart')
    @commands.check(is_allowed)  # Check if the invoker is allowed to use commands
    async def restart(self, ctx):
        global delete_enabled, logout_done, restart_done  # 삭제 기능 및 상태 변수 전역 변수 사용
        if not restart_done:
            delete_enabled = True  # 재시작 시 삭제 기능 다시 활성화
            restart_done = True  # 재시작이 수행됨을 표시
            logout_done = False

            # 봇을 다시 활성화하는 코드 추가
            await self.bot.change_presence(status=discord.Status.online)
            await ctx.send('계엄령을 재선포합니다.')
        else:
            await ctx.send('이미 재시작이 수행되었습니다.')

# Add this cog to the bot
def setup(bot):
    bot.add_cog(AdminCommands(bot))