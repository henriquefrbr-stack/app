from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import requests
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# TMDB API configuration
TMDB_API_KEY = os.environ['TMDB_API_KEY']
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class Movie(BaseModel):
    id: int
    title: str
    overview: str
    poster_path: Optional[str] = None
    release_date: Optional[str] = None
    vote_average: Optional[float] = None
    vote_count: Optional[int] = None
    poster_url: Optional[str] = None

class MovieSearchResponse(BaseModel):
    results: List[Movie]
    total_results: int

class MovieNetwork(BaseModel):
    central_movie: Movie
    related_movies: List[Movie]


# TMDB API helper functions
def get_tmdb_headers():
    return {
        "accept": "application/json"
    }

def process_movie_data(movie_data: dict) -> Movie:
    """Process raw TMDB movie data into our Movie model"""
    poster_url = None
    if movie_data.get('poster_path'):
        poster_url = f"{TMDB_IMAGE_BASE_URL}{movie_data['poster_path']}"
    
    return Movie(
        id=movie_data['id'],
        title=movie_data['title'],
        overview=movie_data.get('overview', ''),
        poster_path=movie_data.get('poster_path'),
        release_date=movie_data.get('release_date'),
        vote_average=movie_data.get('vote_average'),
        vote_count=movie_data.get('vote_count'),
        poster_url=poster_url
    )


# Existing routes
@api_router.get("/")
async def root():
    return {"message": "Movie Recommendation API"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]


# Movie API routes
@api_router.get("/movies/search", response_model=MovieSearchResponse)
async def search_movies(query: str):
    """Search for movies using TMDB API"""
    try:
        url = f"{TMDB_BASE_URL}/search/movie"
        params = {
            "query": query,
            "include_adult": False,
            "language": "en-US",
            "page": 1
        }
        headers = get_tmdb_headers()
        
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        # Process movies
        movies = []
        for movie_data in data.get('results', []):
            try:
                movie = process_movie_data(movie_data)
                movies.append(movie)
            except Exception as e:
                logger.warning(f"Error processing movie data: {e}")
                continue
        
        return MovieSearchResponse(
            results=movies,
            total_results=data.get('total_results', 0)
        )
        
    except requests.RequestException as e:
        logger.error(f"TMDB API error: {e}")
        raise HTTPException(status_code=500, detail="Error fetching movie data")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/movies/{movie_id}/network", response_model=MovieNetwork)
async def get_movie_network(movie_id: int):
    """Get a movie and its related movies for network visualization"""
    try:
        # Get the main movie details
        movie_url = f"{TMDB_BASE_URL}/movie/{movie_id}"
        headers = get_tmdb_headers()
        
        movie_response = requests.get(movie_url, headers=headers)
        movie_response.raise_for_status()
        movie_data = movie_response.json()
        
        central_movie = process_movie_data(movie_data)
        
        # Get similar movies
        similar_url = f"{TMDB_BASE_URL}/movie/{movie_id}/similar"
        similar_response = requests.get(similar_url, headers=headers)
        similar_response.raise_for_status()
        similar_data = similar_response.json()
        
        # Get recommendations
        recommendations_url = f"{TMDB_BASE_URL}/movie/{movie_id}/recommendations"
        rec_response = requests.get(recommendations_url, headers=headers)
        rec_response.raise_for_status()
        rec_data = rec_response.json()
        
        # Combine and process related movies
        related_movies = []
        all_related = similar_data.get('results', []) + rec_data.get('results', [])
        
        # Remove duplicates and limit to 10 movies
        seen_ids = set()
        for movie_data in all_related:
            if movie_data['id'] not in seen_ids and len(related_movies) < 10:
                try:
                    movie = process_movie_data(movie_data)
                    related_movies.append(movie)
                    seen_ids.add(movie_data['id'])
                except Exception as e:
                    logger.warning(f"Error processing related movie data: {e}")
                    continue
        
        return MovieNetwork(
            central_movie=central_movie,
            related_movies=related_movies
        )
        
    except requests.RequestException as e:
        logger.error(f"TMDB API error: {e}")
        raise HTTPException(status_code=500, detail="Error fetching movie network data")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/movies/{movie_id}", response_model=Movie)
async def get_movie_details(movie_id: int):
    """Get detailed information about a specific movie"""
    try:
        url = f"{TMDB_BASE_URL}/movie/{movie_id}"
        headers = get_tmdb_headers()
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        movie_data = response.json()
        return process_movie_data(movie_data)
        
    except requests.RequestException as e:
        logger.error(f"TMDB API error: {e}")
        raise HTTPException(status_code=500, detail="Error fetching movie details")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()