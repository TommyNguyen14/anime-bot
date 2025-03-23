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

    async def show_help(self, ctx):
        embed = discord.Embed(
            title="Character Guessing Game",
            description="Test your anime knowledge by guessing characters!",
            color=self.EMBED_COLOR
        )
        
        # Commands section
        commands_text = (
            "`c` - Start a new character guessing game\n"
            "`c end` - End the current game\n"
            "`clist <anime>` - List characters from an anime"
        )
        embed.add_field(
            name="Commands",
            value=commands_text,
            inline=False
        )
        
        # How to Play section
        gameplay_text = (
            "1. Start a game using `;c`\n"
            "2. Type the character's name to make a guess\n"
            "3. Use 🔄 to skip/start new game at any time\n"
            "4. Use ❌ to end game and see summary\n"
            "5. All commands use the `;` prefix"
        )
        embed.add_field(
            name="How to Play",
            value=gameplay_text,
            inline=False
        )

        # Additional Info section
        info_text = (
            "• Characters are from various anime series\n"
            "• Correct guesses are marked with ✅\n"
            "• Wrong guesses are marked with ❌\n"
            "• Game summary shows all characters attempted"
        )
        embed.add_field(
            name="Additional Info",
            value=info_text,
            inline=False
        )

        embed.set_footer(text=f"Prefix: {Config.PREFIX}")
        
        await ctx.send(embed=embed)

    @commands.command(name="help")
    async def help(self, ctx):
        """Show help information"""
        await self.show_help(ctx)

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