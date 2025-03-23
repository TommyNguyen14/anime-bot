import sys
import os
import json
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
import time

# Add the parent directory to sys.path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.jikan_api import JikanAPI

class DataFetcher:
    def __init__(self):
        self.api = JikanAPI()
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.progress_file = self.cache_dir / "fetch_progress.json"

    def load_progress(self):
        """Load progress from previous run"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'processed_anime': [], 'characters': []}

    def save_progress(self, progress):
        """Save current progress"""
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

    async def fetch_and_save_data(self):
        try:
            print("Starting comprehensive data fetch...")
            
            # Load previous progress
            progress = self.load_progress()
            processed_anime = set(progress['processed_anime'])
            characters = progress['characters']
            
            # Fetch all qualifying anime
            anime_list = await self.api.get_all_anime(min_score=6.0, min_popularity=1000)
            if not anime_list:
                print("Failed to fetch anime list")
                return

            print(f"\nFound {len(anime_list)} qualifying anime series. Processing in batches...")
            
            batch_size = 5  # Reduced batch size for better reliability
            for i in range(0, len(anime_list), batch_size):
                batch = anime_list[i:i + batch_size]
                print(f"\nProcessing batch {i//batch_size + 1}/{(len(anime_list) + batch_size - 1)//batch_size}")
                
                for anime in batch:
                    anime_id = str(anime['mal_id'])
                    if anime_id in processed_anime:
                        print(f"Skipping already processed anime: {anime.get('title')}")
                        continue

                    try:
                        print(f"\nProcessing anime: {anime.get('title')}")
                        
                        # Get full anime details
                        anime_details = await self.api.get_anime_details(anime['mal_id'])
                        if anime_details:
                            anime['title_english'] = anime_details.get('title_english')
                            print(f"Found English title: {anime['title_english']}")
                        
                        # Get characters
                        chars = await self.api.get_anime_characters(anime['mal_id'], anime)
                        if chars:
                            print(f"Found {len(chars)} main characters")
                            characters.extend(chars)
                        
                        processed_anime.add(anime_id)
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        print(f"Error processing anime {anime.get('title')}: {e}")
                        continue
                
                # Save progress after each batch
                self.save_progress({
                    'processed_anime': list(processed_anime),
                    'characters': characters
                })
                
                with open(self.cache_dir / "characters.json", 'w', encoding='utf-8') as f:
                    json.dump(characters, f, ensure_ascii=False, indent=2)
                print(f"\nProgress: {len(characters)} characters from {len(processed_anime)} anime series")
                
                await asyncio.sleep(2)

            print("\nData fetch completed successfully!")
            print(f"Final statistics:")
            print(f"- Total anime processed: {len(processed_anime)}")
            print(f"- Total characters saved: {len(characters)}")
            
            # Update timestamp
            with open(self.cache_dir / "last_update.txt", 'w') as f:
                f.write(datetime.now().isoformat())
            
            # Clean up progress file
            if self.progress_file.exists():
                self.progress_file.unlink()
            
        except Exception as e:
            print(f"Error during data fetch: {e}")
        finally:
            await self.api.cleanup()  # Ensure session is closed properly

    async def cleanup(self):
        """Cleanup resources"""
        if self.api.session:
            await self.api.session.close()

async def main():
    fetcher = DataFetcher()
    await fetcher.fetch_and_save_data()

if __name__ == "__main__":
    asyncio.run(main()) 