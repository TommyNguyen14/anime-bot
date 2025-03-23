import discord
from discord.ext import commands
from utils.database import AnimeDatabase

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db  # Use bot's database instance

    def create_stats_embed(self, title, description, color=discord.Color.blue()):
        """Create a consistent embed style for stats"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        embed.set_footer(text="Data from MyAnimeList", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        return embed

    @commands.command(name='stats', help='Show your guessing statistics')
    async def stats(self, ctx, user: discord.Member = None):
        """Show guessing statistics for a user"""
        target_user = user or ctx.author
        stats = self.db.get_user_stats(target_user.id)
        
        # Get character stats
        char_stats = stats.get('characters', {'correct': 0, 'total': 0})
        char_win_rate = (char_stats['correct'] / char_stats['total'] * 100) if char_stats['total'] > 0 else 0
        
        # Get opening stats
        op_stats = stats.get('openings', {'correct': 0, 'total': 0})
        op_win_rate = (op_stats['correct'] / op_stats['total'] * 100) if op_stats['total'] > 0 else 0
        
        embed = self.create_stats_embed(
            f"📊 {target_user.name}'s Stats",
            "Your guessing game statistics:\n\n"
            f"**Character Guessing:**\n"
            f"• Correct Guesses: {char_stats['correct']}\n"
            f"• Total Games: {char_stats['total']}\n"
            f"• Win Rate: {char_win_rate:.1f}%\n\n"
            f"**Opening Guessing:**\n"
            f"• Correct Guesses: {op_stats['correct']}\n"
            f"• Total Games: {op_stats['total']}\n"
            f"• Win Rate: {op_win_rate:.1f}%",
            discord.Color.blue()
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Stats(bot)) 