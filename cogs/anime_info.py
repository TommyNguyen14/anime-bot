import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import random

class AnimeInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://myanimelist.net"

    def create_info_embed(self, title, description, color=discord.Color.blue()):
        """Create a consistent embed style for anime information"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        embed.set_footer(text="AniGuessr Anime Info", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        return embed

    @commands.command(name='anime')
    async def search_anime(self, ctx, *, query):
        """Search for anime information from MyAnimeList"""
        async with aiohttp.ClientSession() as session:
            # Search for the anime
            search_url = f'{self.base_url}/anime.php?q={query}'
            async with session.get(search_url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find the first anime result
                    anime_link = soup.find('a', {'class': 'hoverinfo_trigger'})
                    if anime_link:
                        anime_url = anime_link['href']
                        async with session.get(anime_url) as anime_response:
                            if anime_response.status == 200:
                                anime_html = await anime_response.text()
                                anime_soup = BeautifulSoup(anime_html, 'html.parser')
                                
                                # Extract information
                                title = anime_soup.find('h1', {'class': 'title-name'}).text.strip()
                                synopsis = anime_soup.find('p', {'itemprop': 'description'}).text.strip()
                                
                                # Get additional info
                                info_div = anime_soup.find('div', {'class': 'information'})
                                info_text = info_div.text.strip() if info_div else "No additional information available"
                                
                                # Get score and popularity
                                score = anime_soup.find('div', {'class': 'score-label'})
                                score_text = score.text.strip() if score else "N/A"
                                
                                popularity = anime_soup.find('span', {'class': 'information popularity'})
                                popularity_text = popularity.text.strip() if popularity else "N/A"
                                
                                # Create embed
                                embed = self.create_info_embed(
                                    title,
                                    synopsis[:1000] + '...' if len(synopsis) > 1000 else synopsis,
                                    discord.Color.blue()
                                )
                                embed.add_field(name="Score", value=score_text, inline=True)
                                embed.add_field(name="Popularity", value=popularity_text, inline=True)
                                embed.add_field(name="Additional Information", value=info_text, inline=False)
                                embed.url = anime_url
                                
                                # Try to get the anime cover image
                                image_div = anime_soup.find('div', {'class': 'leftside'})
                                if image_div:
                                    img = image_div.find('img')
                                    if img and img.get('data-src'):
                                        embed.set_thumbnail(url=img['data-src'])
                                
                                await ctx.send(embed=embed)
                            else:
                                await ctx.send("Couldn't fetch anime details.")
                    else:
                        await ctx.send("Anime not found.")
                else:
                    await ctx.send("Error searching for anime.")

    @commands.command(name='random_anime')
    async def get_random_anime(self, ctx):
        """Get a random anime recommendation"""
        async with aiohttp.ClientSession() as session:
            # Get a random page from the top anime list
            page = random.randint(1, 10)
            url = f'{self.base_url}/topanime.php?limit={50 * (page - 1)}'
            
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find all anime entries
                    anime_entries = soup.find_all('tr', {'class': 'ranking-list'})
                    if anime_entries:
                        random_anime = random.choice(anime_entries)
                        title = random_anime.find('a', {'class': 'hoverinfo_trigger'}).text.strip()
                        score = random_anime.find('td', {'class': 'score'}).text.strip()
                        
                        # Get the anime URL
                        anime_url = random_anime.find('a', {'class': 'hoverinfo_trigger'})['href']
                        
                        embed = self.create_info_embed(
                            "🎲 Random Anime Recommendation",
                            f"**{title}**\nScore: {score}",
                            discord.Color.green()
                        )
                        embed.url = anime_url
                        
                        # Try to get the anime thumbnail
                        img = random_anime.find('img')
                        if img and img.get('data-src'):
                            embed.set_thumbnail(url=img['data-src'])
                        
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("Couldn't find any anime recommendations.")
                else:
                    await ctx.send("Error fetching anime recommendations.")

    @commands.command(name='seasonal')
    async def get_seasonal_anime(self, ctx):
        """Get current seasonal anime"""
        async with aiohttp.ClientSession() as session:
            url = f'{self.base_url}/anime/season'
            
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find seasonal anime entries
                    seasonal_anime = soup.find_all('div', {'class': 'seasonal-anime'})
                    if seasonal_anime:
                        # Get up to 5 random seasonal anime
                        selected_anime = random.sample(seasonal_anime, min(5, len(seasonal_anime)))
                        
                        embed = self.create_info_embed(
                            "🌸 Current Seasonal Anime",
                            "Here are some anime from the current season:\n\n",
                            discord.Color.purple()
                        )
                        
                        for anime in selected_anime:
                            title = anime.find('p', {'class': 'title'}).text.strip()
                            synopsis = anime.find('div', {'class': 'synopsis'}).text.strip()
                            score = anime.find('div', {'class': 'score'}).text.strip()
                            
                            embed.add_field(
                                name=f"{title} (Score: {score})",
                                value=synopsis[:200] + '...' if len(synopsis) > 200 else synopsis,
                                inline=False
                            )
                        
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("Couldn't find seasonal anime information.")
                else:
                    await ctx.send("Error fetching seasonal anime information.")

async def setup(bot):
    await bot.add_cog(AnimeInfo(bot)) 