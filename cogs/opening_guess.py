import discord
from discord.ext import commands
import random
from utils.database import AnimeDatabase

class OpeningGuess(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        self.db = self.bot.db
        self._locks = {}  # Channel-specific locks

    def create_game_embed(self, title, description, color=discord.Color.default()):
        """Create a consistent embed style for the game"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=0x000000  # Black color
        )
        embed.set_footer(text="Data from MyAnimeList", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        return embed

    @commands.command(name='op', aliases=['op_start'], help='Start a new opening guessing game')
    async def op_start(self, ctx, difficulty: str = None):
        """Start a new opening guessing game"""
        channel_id = ctx.channel.id

        # Check for active game
        if channel_id in self.active_games:
            await ctx.send("A game is already in progress in this channel! End it with `!op_end`")
            return

        try:
            # Validate and get opening
            if difficulty:
                difficulty = difficulty.lower()
                if difficulty not in ['easy', 'medium', 'hard']:
                    await ctx.send("Invalid difficulty! Choose from: Easy, Medium, Hard")
                    return

            opening = self.db.get_random_opening(difficulty)
            if not opening:
                await ctx.send("No openings available. Please try again later.")
                return

            # Initialize game state
            self.active_games[channel_id] = {
                'opening': opening,
                'hints_used': 0,
                'guesses': 0,
                'started_by': ctx.author.id
            }

            # Create initial embed
            embed = discord.Embed(
                title="🎵 Guess the Anime Opening!",
                description=(
                    "Try to guess which anime this opening is from!\n\n"
                    f"Difficulty: **{opening.get('difficulty', 'Unknown').title()}**\n"
                    "Use `!hint` for hints or just type your guess!"
                ),
                color=0x000000
            )

            # Use anime thumbnail instead of YouTube thumbnail
            if opening.get('anime_data', {}).get('images', {}).get('jpg', {}).get('large_image_url'):
                embed.set_image(url=opening['anime_data']['images']['jpg']['large_image_url'])

            await ctx.send(embed=embed)

        except Exception as e:
            if channel_id in self.active_games:
                del self.active_games[channel_id]
            await ctx.send(f"An error occurred while starting the game: {str(e)}")

    @commands.command(name='hint', help='Get a hint for the current opening')
    async def hint(self, ctx):
        """Get a hint for the current opening"""
        channel_id = ctx.channel.id
        if channel_id not in self.active_games:
            await ctx.send("No active game! Start one with `!op`")
            return

        game = self.active_games[channel_id]
        opening = game['opening']

        # Modified hints without YouTube link
        hints = [
            f"The artist is **{opening['artist']}**",
            f"The opening name starts with **{opening['name'][0]}**",
            f"This opening is from a {opening['anime_data']['score']}/10 rated anime",
            f"The opening name is **{opening['name']}**"  # Changed last hint
        ]

        if game['hints_used'] >= len(hints):
            await ctx.send("No more hints available!")
            return

        hint = hints[game['hints_used']]
        game['hints_used'] += 1

        embed = discord.Embed(
            title=f"💡 Hint #{game['hints_used']}",
            description=hint,
            color=0x000000
        )

        await ctx.send(embed=embed)

    @commands.command(name='op_skip', help='Skip the current opening')
    async def op_skip(self, ctx):
        """Skip the current opening"""
        if ctx.channel.id not in self.active_games:
            await ctx.send("No active game! Start one with `!op_start`")
            return

        game = self.active_games[ctx.channel.id]
        if ctx.author.id != game['started_by']:
            await ctx.send("Only the game starter can skip!")
            return

        # Update stats for skipped game
        self.db.update_stats(ctx.author.id, 'openings', False)

        embed = self.create_game_embed(
            "⏭️ Opening Skipped",
            f"The opening was **{game['opening']['name']}**\n"
            f"**Anime:** {game['opening']['anime']}\n"
            f"**Artist:** {game['opening']['artist']}\n"
            f"**Type:** {game['opening']['type']}",
            discord.Color.orange()
        )

        if game['opening'].get('thumbnail_url'):
            embed.set_image(url=game['opening']['thumbnail_url'])

        await ctx.send(embed=embed)
        del self.active_games[ctx.channel.id]

    @commands.command(name='op_end', help='End the current opening guessing game')
    async def op_end(self, ctx):
        """End the current opening guessing game"""
        channel_id = ctx.channel.id
        if channel_id not in self.active_games:
            await ctx.send("No active game to end!")
            return

        game = self.active_games[channel_id]
        if ctx.author.id != game['started_by'] and not ctx.author.guild_permissions.manage_messages:
            await ctx.send("Only the game starter or moderators can end the game!")
            return

        opening = game['opening']
        embed = discord.Embed(
            title="Game Ended",
            description=(
                f"The opening was **{opening['name']}**\n"
                f"From the anime: **{opening['anime']}**\n"
                f"Artist: **{opening['artist']}**"
            ),
            color=0x000000
        )

        if opening.get('thumbnail_url'):
            embed.set_image(url=opening['thumbnail_url'])

        await ctx.send(embed=embed)
        del self.active_games[channel_id]

    @commands.command(name='op_leaderboard', help='Show the opening guessing leaderboard')
    async def op_leaderboard(self, ctx):
        """Show the opening guessing leaderboard"""
        leaderboard = self.db.get_leaderboard('openings')
        if not leaderboard:
            await ctx.send("No games have been played yet!")
            return

        embed = self.create_game_embed(
            "🏆 Opening Guessing Leaderboard",
            "Top players by correct guesses:\n\n",
            discord.Color.gold()
        )

        for i, entry in enumerate(leaderboard, 1):
            user = self.bot.get_user(int(entry['user_id']))
            if user:
                embed.add_field(
                    name=f"{i}. {user.name}",
                    value=f"Correct: {entry['correct']}\n"
                          f"Total: {entry['total']}\n"
                          f"Win Rate: {entry['win_rate']:.1f}%",
                    inline=False
                )

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle message events"""
        if message.author.bot or not message.content:
            return
        
        channel_id = message.channel.id
        if channel_id not in self.active_games:
            return
        
        # Skip if it's a command
        if message.content.startswith('!'):
            return
        
        # Use channel-specific lock
        if hasattr(self, f'_lock_{channel_id}'):
            return
        
        try:
            setattr(self, f'_lock_{channel_id}', True)
            game = self.active_games[channel_id]
            guess = message.content.lower()
            correct_name = game['opening']['anime'].lower()
            
            # Check for correct guess
            if guess == correct_name or self.is_similar_name(guess, correct_name):
                await self.handle_correct_guess(message, game)
            else:
                game['guesses'] += 1
                await message.add_reaction('❌')
        finally:
            delattr(self, f'_lock_{channel_id}')

    async def handle_correct_guess(self, message, game):
        """Handle correct opening guess"""
        self.db.update_stats(str(message.author.id), 'openings', True)
        
        embed = discord.Embed(
            title="🎉 Correct!",
            description=(
                f"{message.author.mention} got it in {game['guesses']} guesses!\n\n"
                f"**Opening:** {game['opening']['name']}\n"
                f"**Anime:** {game['opening']['anime']}\n"
                f"**Artist:** {game['opening']['artist']}"
            ),
            color=0x000000
        )
        
        if game['opening'].get('anime_data', {}).get('images', {}).get('jpg', {}).get('large_image_url'):
            embed.set_image(url=game['opening']['anime_data']['images']['jpg']['large_image_url'])
        
        await message.channel.send(embed=embed)
        del self.active_games[message.channel.id]

    def is_similar_name(self, guess: str, correct: str) -> bool:
        """Check if the guessed name is similar enough to the correct name"""
        guess = guess.lower().strip()
        correct = correct.lower().strip()
        
        # Direct match
        if guess == correct:
            return True
        
        # Remove common prefixes/suffixes
        prefixes = ['the ', 'a ', 'an ']
        for prefix in prefixes:
            if guess.startswith(prefix):
                guess = guess[len(prefix):]
            if correct.startswith(prefix):
                correct = correct[len(prefix):]
        
        # Check if one is contained in the other (for nickname matches)
        if len(guess) > 3 and (guess in correct or correct in guess):
            return True
        
        return False

async def setup(bot):
    await bot.add_cog(OpeningGuess(bot)) 