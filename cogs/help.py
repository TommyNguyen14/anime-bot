import discord
from discord.ext import commands
from discord.ui import View, Button
from typing import List, Dict
from discord import app_commands
from utils.config import Config

class HelpView(View):
    def __init__(self, pages: List[discord.Embed], stats: Dict):
        super().__init__(timeout=180)  # 3 minute timeout
        self.pages = pages
        self.current_page = 0
        self.stats = stats
        
        # Add navigation buttons
        self.add_item(Button(label="◀", custom_id="prev", style=discord.ButtonStyle.primary, disabled=True))
        self.add_item(Button(label="▶", custom_id="next", style=discord.ButtonStyle.primary))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.data["custom_id"] == "prev":
            if self.current_page > 0:
                self.current_page -= 1
                # Update button states
                self.children[0].disabled = self.current_page == 0
                self.children[1].disabled = self.current_page == len(self.pages) - 1
                await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
        elif interaction.data["custom_id"] == "next":
            if self.current_page < len(self.pages) - 1:
                self.current_page += 1
                # Update button states
                self.children[0].disabled = self.current_page == 0
                self.children[1].disabled = self.current_page == len(self.pages) - 1
                await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
        return True

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._locks = {}
        self.EMBED_COLOR = Config.DEFAULT_COLOR

    @commands.hybrid_command(name="help")
    async def help(self, ctx):
        """Show help information"""
        await self.show_help(ctx)

    async def show_help(self, ctx):
        embed = discord.Embed(
            title=Config.HELP_TITLE,
            description=Config.HELP_DESCRIPTION,
            color=self.EMBED_COLOR
        )
        
        embed.add_field(
            name="📝 Commands",
            value=Config.get_commands_help(),
            inline=False
        )
        
        embed.add_field(
            name="🎯 How to Play",
            value=Config.get_gameplay_help(),
            inline=False
        )

        embed.set_footer(text=f"Prefix: {Config.PREFIX}")
        
        await ctx.send(embed=embed)

    @commands.command()
    async def ping(self, ctx):
        """Check bot latency"""
        channel_id = ctx.channel.id
        if channel_id in self._locks:
            return
            
        try:
            self._locks[channel_id] = True
            latency = round(self.bot.latency * 1000)
            await ctx.send(f"Pong! Latency: {latency}ms")
        finally:
            self._locks.pop(channel_id, None)

async def setup(bot):
    print("Setting up Help cog...")
    try:
        await bot.add_cog(Help(bot))
        print("Help cog setup complete!")
    except Exception as e:
        print(f"Error setting up Help cog: {str(e)}")
        raise e 