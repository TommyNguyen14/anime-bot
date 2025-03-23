import asyncio
import json
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

class CacheUpdater:
    def __init__(self):
        self.base_url = "https://api.jikan.moe/v4"
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize cache files
        self.characters_file = self.cache_dir / "characters.json"
        self.last_update_file = self.cache_dir / "last_update.txt"
        
        # Load existing cache
        self.existing_characters = self.load_existing_cache()
        self.existing_char_ids = {char['id'] for char in self.existing_characters}
        self.existing_anime_ids = {char['anime_data']['mal_id'] for char in self.existing_characters if 'anime_data' in char and 'mal_id' in char['anime_data']}
        
        # Rate limiting
        self.session = None
        self.last_request_time = 0
        self.rate_limit_delay = 1  # seconds between requests

    def load_existing_cache(self) -> List[Dict]:
        """Load existing character cache"""
        try:
            with open(self.characters_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    async def init_session(self):
        """Initialize aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def make_request(self, endpoint: str) -> Dict:
        """Make a rate-limited API request"""
        await asyncio.sleep(self.rate_limit_delay)
        
        try:
            async with self.session.get(f"{self.base_url}/{endpoint}") as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:  # Rate limited
                    print("Rate limited, waiting 60 seconds...")
                    await asyncio.sleep(60)
                    return await self.make_request(endpoint)
                else:
                    print(f"Error {response.status} for {endpoint}")
                    return None
        except Exception as e:
            print(f"Error making request to {endpoint}: {e}")
            return None

    async def get_seasonal_anime(self) -> Set[int]:
        """Get currently airing and upcoming anime IDs"""
        anime_ids = set()
        
        # Get current season and year
        now = datetime.now()
        year = now.year
        
        # Map month to season
        if now.month in (1, 2, 3):
            current_season = "winter"
        elif now.month in (4, 5, 6):
            current_season = "spring"
        elif now.month in (7, 8, 9):
            current_season = "summer"
        else:
            current_season = "fall"
            
        # Calculate next season
        seasons_order = ["winter", "spring", "summer", "fall"]
        current_idx = seasons_order.index(current_season)
        next_season = seasons_order[(current_idx + 1) % 4]
        next_year = year + 1 if next_season == "winter" else year
        
        # Fetch current and upcoming season
        seasons_to_fetch = [
            (year, current_season),
            (next_year, next_season)
        ]
        
        for year, season in seasons_to_fetch:
            print(f"Fetching {season} {year} anime...")
            data = await self.make_request(f"seasons/{year}/{season}")
            if data and 'data' in data:
                for anime in data['data']:
                    anime_ids.add(anime['mal_id'])
                    
        # Also fetch currently airing anime
        print("Fetching currently airing anime...")
        page = 1
        while True:
            data = await self.make_request(f"anime?status=airing&page={page}")
            if not data or not data.get('data'):
                break
                
            for anime in data['data']:
                anime_ids.add(anime['mal_id'])
                
            if not data.get('pagination', {}).get('has_next_page'):
                break
                
            page += 1
                    
        return anime_ids

    async def get_top_anime(self, limit: int = 500) -> Set[int]:
        """Get top anime IDs"""
        anime_ids = set()
        page = 1
        
        while len(anime_ids) < limit:
            data = await self.make_request(f"top/anime?page={page}")
            if not data or not data.get('data'):
                break
                
            for anime in data['data']:
                anime_ids.add(anime['mal_id'])
            
            page += 1
            
        return anime_ids

    async def process_anime(self, anime_id: int) -> List[Dict]:
        """Process an anime and its characters"""
        # Get anime details
        anime_data = await self.make_request(f"anime/{anime_id}/full")
        if not anime_data or not anime_data.get('data'):
            return []

        anime = anime_data['data']
        
        # Get characters
        char_data = await self.make_request(f"anime/{anime_id}/characters")
        if not char_data or not char_data.get('data'):
            return []

        processed_chars = []
        for char in char_data['data']:
            if char['role'] != 'Main':
                continue

            char_id = str(char['character']['mal_id'])
            if char_id in self.existing_char_ids:
                continue

            # Get detailed character info
            char_details = await self.make_request(f"characters/{char_id}/full")
            if not char_details or not char_details.get('data'):
                continue

            char_info = char_details['data']
            
            try:
                # Safely get numeric values with proper type conversion
                def safe_int(value, default=99999):
                    try:
                        return int(value) if value is not None else default
                    except (ValueError, TypeError):
                        return default
                        
                def safe_float(value, default=0.0):
                    try:
                        return float(value) if value is not None else default
                    except (ValueError, TypeError):
                        return default

                character_data = {
                    'id': char_id,
                    'name': char_info['name'],
                    'image_url': char_info['images']['jpg']['image_url'],
                    'favorites': safe_int(char_info.get('favorites'), 0),
                    'anime_data': {
                        'mal_id': anime['mal_id'],
                        'title': anime['title'],
                        'english_title': anime.get('title_english'),
                        'images': anime['images'],
                        'popularity': safe_int(anime.get('popularity'), 99999),
                        'members': safe_int(anime.get('members'), 0),
                        'score': safe_float(anime.get('score'), 0.0),
                        'rank': safe_int(anime.get('rank'), 99999)
                    }
                }
                
                # Set difficulty based on favorites
                favorites = character_data['favorites']
                if favorites > 10000:
                    character_data['difficulty'] = "Easy"
                elif favorites > 5000:
                    character_data['difficulty'] = "Medium"
                else:
                    character_data['difficulty'] = "Hard"
                    
                processed_chars.append(character_data)
                self.existing_char_ids.add(char_id)
                print(f"Added character: {character_data['name']} from {anime['title']}")
                
            except (KeyError, ValueError) as e:
                print(f"Error processing character {char_id}: {e}")
                continue

        return processed_chars

    async def update_cache(self):
        """Update the cache with new characters"""
        try:
            await self.init_session()
            
            # Get anime IDs to process
            print("Getting seasonal and top anime...")
            anime_ids = await self.get_seasonal_anime()
            top_anime = await self.get_top_anime(500)
            anime_ids.update(top_anime)
            
            # Remove already processed anime
            new_anime_ids = anime_ids - self.existing_anime_ids
            print(f"Found {len(new_anime_ids)} new anime to process")
            
            # Process new anime and their characters
            new_characters = []
            for anime_id in new_anime_ids:
                chars = await self.process_anime(anime_id)
                new_characters.extend(chars)
                
            # Update the cache
            if new_characters:
                updated_cache = self.existing_characters + new_characters
                with open(self.characters_file, 'w', encoding='utf-8') as f:
                    json.dump(updated_cache, f, ensure_ascii=False, indent=2)
                    
                # Update timestamp
                with open(self.last_update_file, 'w') as f:
                    f.write(datetime.now().isoformat())
                    
                print(f"Added {len(new_characters)} new characters to the cache")
            else:
                print("No new characters found")
                
        finally:
            await self.close_session()

async def main():
    updater = CacheUpdater()
    await updater.update_cache()

if __name__ == "__main__":
    asyncio.run(main()) 