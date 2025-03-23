from googleapiclient.discovery import build
import os
from dotenv import load_dotenv

class YouTubeAPI:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("YouTube API key not found in .env file")
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    async def search_opening(self, anime_title: str, opening_name: str) -> dict:
        """Search for an anime opening on YouTube"""
        try:
            query = f"{anime_title} {opening_name} opening full"
            request = self.youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=1,
                videoDuration="short"  # Typically openings are "short" duration
            )
            response = request.execute()

            if not response.get('items'):
                return None

            video = response['items'][0]
            return {
                'video_id': video['id']['videoId'],
                'url': f"https://www.youtube.com/watch?v={video['id']['videoId']}",
                'thumbnail_url': video['snippet']['thumbnails']['high']['url']
            }

        except Exception as e:
            print(f"Error searching YouTube: {e}")
            return None 