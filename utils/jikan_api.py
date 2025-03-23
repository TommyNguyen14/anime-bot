import aiohttp
import json
import random
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import time

class JikanAPI:
    def __init__(self):
        self.base_url = "https://api.jikan.moe/v4/"
        self.cached_characters = []
        self.cached_openings = []
        self.cached_anime = {}
        self.last_request = 0
        self.rate_limit = 1
        self.max_retries = 3
        self.session = None
        self.consecutive_429s = 0
        
        # Create data directory if it doesn't exist
        self.data_dir = Path("data/cache")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def _make_request(self, endpoint):
        """Make a request to the Jikan API with improved rate limiting"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        # Adaptive delay based on rate limits
        current_delay = self.rate_limit * (1 + (0.5 * self.consecutive_429s))
        
        now = time.time()
        time_since_last = now - self.last_request
        if time_since_last < current_delay:
            await asyncio.sleep(current_delay - time_since_last)

        url = f"{self.base_url}{endpoint}"
        try:
            async with self.session.get(url) as response:
                self.last_request = time.time()
                
                if response.status == 200:
                    self.consecutive_429s = max(0, self.consecutive_429s - 1)
                    return await response.json()
                elif response.status == 429:
                    self.consecutive_429s += 1
                    wait_time = min(4 * (1 + self.consecutive_429s), 60)  # Cap at 60 seconds
                    print(f"Rate limited on {endpoint}. Waiting {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    return await self._make_request(endpoint)
                else:
                    print(f"Error {response.status} for URL: {url}")
                    return None
        except Exception as e:
            print(f"Request error: {e}")
            return None

    async def get_all_anime(self, min_score=6.0, min_popularity=1000):
        """Get all qualifying TV anime with improved fetching and error handling"""
        print("Fetching all qualifying TV anime series...")
        anime_list = []
        existing_ids = set()
        
        # First get top anime by score
        print("\nPhase 1: Fetching anime by score...")
        page = 1
        while True:
            print(f"Fetching score-based page {page}...")
            data = await self._make_request(f"anime?page={page}&type=tv&order_by=score&sort=desc")
            
            if not data or not data.get('data'):
                break
                
            new_items = [
                anime for anime in data['data']
                if (anime.get('type') == 'TV' and
                    not anime.get('title', '').lower().endswith('ova') and
                    not anime.get('title', '').lower().endswith('movie') and
                    anime['mal_id'] not in existing_ids and
                    (anime.get('score') is not None and float(anime.get('score', 0)) >= min_score))
            ]
            
            if new_items:
                anime_list.extend(new_items)
                existing_ids.update(anime['mal_id'] for anime in new_items)
                print(f"Added {len(new_items)} anime (Total: {len(anime_list)})")
            
            if len(data['data']) < 25 or page >= data['pagination']['last_visible_page']:
                break
                
            page += 1
            await asyncio.sleep(1)

        # Then get top anime by popularity
        print("\nPhase 2: Fetching anime by popularity...")
        page = 1
        while True:
            print(f"Fetching popularity-based page {page}...")
            data = await self._make_request(f"anime?page={page}&type=tv&order_by=popularity&sort=asc")
            
            if not data or not data.get('data'):
                break
                
            new_items = [
                anime for anime in data['data']
                if (anime.get('type') == 'TV' and
                    not anime.get('title', '').lower().endswith('ova') and
                    not anime.get('title', '').lower().endswith('movie') and
                    anime['mal_id'] not in existing_ids and
                    (anime.get('popularity') is not None and 
                     int(anime.get('popularity', 99999)) <= min_popularity))
            ]
            
            if new_items:
                anime_list.extend(new_items)
                existing_ids.update(anime['mal_id'] for anime in new_items)
                print(f"Added {len(new_items)} popular anime (Total: {len(anime_list)})")
            
            if (len(data['data']) < 25 or 
                page >= data['pagination']['last_visible_page'] or 
                all(anime.get('popularity', 99999) > min_popularity for anime in data['data'])):
                break
                
            page += 1
            await asyncio.sleep(1)

        # Clean and validate the data before returning
        validated_list = []
        for anime in anime_list:
            try:
                # Ensure all required fields are present and valid
                validated_anime = {
                    'mal_id': anime['mal_id'],
                    'title': anime.get('title', 'Unknown Title'),
                    'title_english': anime.get('title_english'),
                    'score': float(anime.get('score', 0)) if anime.get('score') is not None else 0,
                    'popularity': int(anime.get('popularity', 99999)),
                    'type': anime.get('type', 'TV'),
                    'members': int(anime.get('members', 0)),
                    'favorites': int(anime.get('favorites', 0)),
                    'rank': int(anime.get('rank', 99999)) if anime.get('rank') is not None else 99999
                }
                validated_list.append(validated_anime)
            except (ValueError, TypeError) as e:
                print(f"Skipping invalid anime data: {anime.get('title', 'Unknown')} - Error: {e}")
                continue

        print(f"\nTotal valid unique TV anime fetched: {len(validated_list)}")
        return sorted(validated_list, key=lambda x: x.get('popularity', 99999))

    async def get_anime_characters(self, anime_id, anime_data):
        """Get characters for an anime with improved error handling"""
        print(f"Fetching characters for {anime_data.get('title', anime_id)}...")
        data = await self._make_request(f"anime/{anime_id}/characters")
        if not data or not data.get('data'):
            return []
            
        characters = []
        for char in data['data']:
            if char['role'] == 'Main':
                try:
                    character_data = {
                        'id': str(char['character']['mal_id']),
                        'name': char['character']['name'],
                        'image_url': char['character']['images']['jpg']['image_url'],
                        'favorites': int(char.get('favorites', 0)),
                        'anime_data': {
                            'title': anime_data['title'],
                            'english_title': anime_data.get('title_english'),
                            'popularity': int(anime_data.get('popularity', 99999)),
                            'members': int(anime_data.get('members', 0)),
                            'score': float(anime_data.get('score', 0)),
                            'rank': int(anime_data.get('rank', 99999))
                        }
                    }
                    # Set difficulty based on favorites
                    if character_data['favorites'] > 10000:
                        character_data['difficulty'] = "Easy"
                    elif character_data['favorites'] > 5000:
                        character_data['difficulty'] = "Medium"
                    else:
                        character_data['difficulty'] = "Hard"
                        
                    characters.append(character_data)
                except (ValueError, TypeError, KeyError) as e:
                    print(f"Error processing character from {anime_data.get('title')}: {e}")
                    continue
                
        return characters

    async def get_character_details(self, char_id):
        """Get detailed character information"""
        data = await self._make_request(f"characters/{char_id}/full")
        if data and data.get('data'):
            return data['data']
        return None

    async def get_anime_details(self, anime_id):
        """Get detailed anime information"""
        data = await self._make_request(f"anime/{anime_id}/full")
        if data and data.get('data'):
            return data['data']
        return None

    async def get_anime_themes(self, anime_id, anime_data):
        """Get opening themes for an anime"""
        data = await self._make_request(f"anime/{anime_id}/themes")
        if not data or not data.get('data') or not data['data'].get('openings'):
            return []
            
        openings = []
        
        for theme in data['data']['openings']:
            # Parse theme text
            theme_parts = theme.split(' by ')
            song_name = theme_parts[0].strip('"')
            artist = theme_parts[1] if len(theme_parts) > 1 else None
            
            opening_data = {
                'id': f"{anime_id}_{theme}",
                'name': song_name,
                'artist': artist or "Unknown",
                'anime': anime_data['title'],
                'type': 'OP',
                'anime_data': {
                    'title': anime_data['title'],
                    'popularity': anime_data.get('popularity', 9999),
                    'members': anime_data.get('members', 0),
                    'score': anime_data.get('score', 0),
                    'rank': anime_data.get('rank', 9999)
                }
            }
            
            openings.append(opening_data)
            
        return openings

    def _determine_difficulty(self, anime_data):
        """Determine difficulty based on anime popularity"""
        popularity = anime_data.get('popularity', 9999)
        rank = anime_data.get('rank', 9999)
        
        if popularity <= 100 or rank <= 100:
            return 'easy'
        elif popularity <= 500 or rank <= 500:
            return 'medium'
        else:
            return 'hard'

    async def update_cache(self):
        """Update the cache with fresh data"""
        print("Updating anime cache...")
        
        # Get all anime (limit can be adjusted for testing)
        anime_list = await self.get_all_anime(min_score=6.0, min_popularity=1000)  # Remove limit for production
        if not anime_list:
            print("Failed to fetch anime list")
            return [], []
            
        print(f"Fetched {len(anime_list)} anime series")
        
        # Sort anime by popularity to prioritize well-known series
        anime_list.sort(key=lambda x: x.get('members', 0), reverse=True)
        
        # Process anime in batches
        batch_size = 5  # Increased batch size
        all_characters = []
        all_openings = []
        
        for i in range(0, len(anime_list), batch_size):
            batch = anime_list[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(anime_list) + batch_size - 1)//batch_size}")
            
            # Process each anime in batch
            for anime in batch:
                try:
                    # Get characters
                    chars = await self.get_anime_characters(anime['mal_id'], anime)
                    if chars:
                        for char in chars:
                            char['difficulty'] = self._determine_difficulty(char['anime_data'])
                        all_characters.extend(chars)
                    
                    # Get themes
                    openings = await self.get_anime_themes(anime['mal_id'], anime)
                    if openings:
                        for opening in openings:
                            opening['difficulty'] = self._determine_difficulty(opening['anime_data'])
                        all_openings.extend(openings)
                    
                    # Wait between anime processing
                    await asyncio.sleep(self.rate_limit)
                    
                except Exception as e:
                    print(f"Error processing anime {anime.get('title', anime.get('mal_id'))}: {e}")
                    continue
                
                # Save progress periodically
                if len(all_characters) % 100 == 0 or len(all_openings) % 100 == 0:
                    self._save_progress(all_characters, all_openings)
            
            print(f"Current progress: {len(all_characters)} characters, {len(all_openings)} openings")
        
        print(f"Finished processing all anime. Found {len(all_characters)} characters and {len(all_openings)} openings")
        
        # Update cache
        self.cached_characters = all_characters
        self.cached_openings = all_openings
        
        # Final save
        self._save_cache()
        
        return all_characters, all_openings

    def _save_progress(self, characters, openings):
        """Save current progress to temporary files"""
        try:
            # Save characters progress
            with open(self.data_dir / 'characters_progress.json', 'w', encoding='utf-8') as f:
                json.dump(characters, f, ensure_ascii=False, indent=2)
                
            # Save openings progress
            with open(self.data_dir / 'openings_progress.json', 'w', encoding='utf-8') as f:
                json.dump(openings, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"Error saving progress: {e}")

    def _save_cache(self):
        """Save cached data to files"""
        # Save characters
        with open(self.data_dir / 'characters.json', 'w', encoding='utf-8') as f:
            json.dump(self.cached_characters, f, ensure_ascii=False, indent=2)
            
        # Save openings
        with open(self.data_dir / 'openings.json', 'w', encoding='utf-8') as f:
            json.dump(self.cached_openings, f, ensure_ascii=False, indent=2)
            
        # Save timestamp
        with open(self.data_dir / 'last_update.txt', 'w') as f:
            f.write(datetime.now().isoformat())

    async def cleanup(self):
        """Properly close the session"""
        if self.session:
            await self.session.close() 