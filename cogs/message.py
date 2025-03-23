import discord
from discord.ext import commands

class Message(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='hello')
    async def hello(self, ctx):
        """Responds with a greeting"""
        await ctx.send(f'Hello {ctx.author.name}! 👋')

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore messages from the bot itself
        if message.author == self.bot.user:
            return

        # Process commands
        await self.bot.process_commands(message)

async def setup(bot):
    await bot.add_cog(Message(bot)) 