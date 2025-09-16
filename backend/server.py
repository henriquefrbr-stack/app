from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import requests
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
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

class Genre(BaseModel):
    id: int
    name: str

class CastMember(BaseModel):
    id: int
    name: str
    character: str

class CrewMember(BaseModel):
    id: int
    name: str
    job: str

class Movie(BaseModel):
    id: int
    title: str
    overview: str
    poster_path: Optional[str] = None
    release_date: Optional[str] = None
    vote_average: Optional[float] = None
    vote_count: Optional[int] = None
    poster_url: Optional[str] = None
    genres: Optional[List[Genre]] = None
    cast: Optional[List[CastMember]] = None
    director: Optional[str] = None
    similarity_score: Optional[float] = None

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

def process_movie_data(movie_data: dict, include_details: bool = False) -> Movie:
    """Process raw TMDB movie data into our Movie model"""
    poster_url = None
    if movie_data.get('poster_path'):
        poster_url = f"{TMDB_IMAGE_BASE_URL}{movie_data['poster_path']}"
    
    movie = Movie(
        id=movie_data['id'],
        title=movie_data['title'],
        overview=movie_data.get('overview', ''),
        poster_path=movie_data.get('poster_path'),
        release_date=movie_data.get('release_date'),
        vote_average=movie_data.get('vote_average'),
        vote_count=movie_data.get('vote_count'),
        poster_url=poster_url
    )
    
    # Add detailed information if available
    if include_details:
        if 'genres' in movie_data:
            movie.genres = [Genre(id=g['id'], name=g['name']) for g in movie_data['genres']]
    
    return movie

def get_movie_details(movie_id: int) -> Dict[str, Any]:
    """Get comprehensive movie details including cast and crew"""
    try:
        params = {"api_key": TMDB_API_KEY, "append_to_response": "credits"}
        headers = get_tmdb_headers()
        
        url = f"{TMDB_BASE_URL}/movie/{movie_id}"
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching movie details for {movie_id}: {e}")
        return {}

def calculate_similarity_score(central_movie: Dict[str, Any], candidate_movie: Dict[str, Any]) -> float:
    """Calculate hybrid similarity score based on multiple factors"""
    score = 0.0
    
    # Base TMDB similarity (if available) - 20% weight
    base_score = 0.2
    
    # Genre similarity - 40% weight
    central_genres = set(genre['id'] for genre in central_movie.get('genres', []))
    candidate_genres = set(genre['id'] for genre in candidate_movie.get('genres', []))
    
    if central_genres and candidate_genres:
        genre_overlap = len(central_genres.intersection(candidate_genres))
        max_genres = max(len(central_genres), len(candidate_genres))
        genre_score = (genre_overlap / max_genres) * 0.4
        score += genre_score
    
    # Director similarity - 25% weight
    central_credits = central_movie.get('credits', {})
    candidate_credits = candidate_movie.get('credits', {})
    
    central_director = None
    candidate_director = None
    
    for crew in central_credits.get('crew', []):
        if crew.get('job') == 'Director':
            central_director = crew.get('id')
            break
    
    for crew in candidate_credits.get('crew', []):
        if crew.get('job') == 'Director':
            candidate_director = crew.get('id')
            break
    
    if central_director and candidate_director and central_director == candidate_director:
        score += 0.25
    
    # Cast similarity - 15% weight
    central_cast = set(actor['id'] for actor in central_credits.get('cast', [])[:10])  # Top 10 cast
    candidate_cast = set(actor['id'] for actor in candidate_credits.get('cast', [])[:10])
    
    if central_cast and candidate_cast:
        cast_overlap = len(central_cast.intersection(candidate_cast))
        cast_score = min(cast_overlap / 5, 1.0) * 0.15  # Max score if 5+ actors in common
        score += cast_score
    
    return min(score, 1.0)  # Cap at 1.0

def get_enhanced_recommendations(movie_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get enhanced movie recommendations using hybrid algorithm"""
    try:
        params = {"api_key": TMDB_API_KEY}
        headers = get_tmdb_headers()
        
        # Get central movie details with credits
        central_movie = get_movie_details(movie_id)
        if not central_movie:
            return []
        
        # Get TMDB similar and recommended movies
        similar_url = f"{TMDB_BASE_URL}/movie/{movie_id}/similar"
        similar_response = requests.get(similar_url, params=params, headers=headers)
        similar_data = similar_response.json() if similar_response.status_code == 200 else {'results': []}
        
        recommendations_url = f"{TMDB_BASE_URL}/movie/{movie_id}/recommendations"
        rec_response = requests.get(recommendations_url, params=params, headers=headers)
        rec_data = rec_response.json() if rec_response.status_code == 200 else {'results': []}
        
        # Combine all candidate movies
        candidate_movies = similar_data.get('results', []) + rec_data.get('results', [])
        
        # If we don't have enough candidates, get popular movies from same genres
        if len(candidate_movies) < limit * 2:
            central_genres = central_movie.get('genres', [])
            if central_genres:
                genre_ids = ','.join(str(g['id']) for g in central_genres[:3])  # Top 3 genres
                discover_params = {
                    "api_key": TMDB_API_KEY,
                    "with_genres": genre_ids,
                    "sort_by": "popularity.desc",
                    "page": 1
                }
                discover_url = f"{TMDB_BASE_URL}/discover/movie"
                discover_response = requests.get(discover_url, params=discover_params, headers=headers)
                discover_data = discover_response.json() if discover_response.status_code == 200 else {'results': []}
                candidate_movies.extend(discover_data.get('results', []))
        
        # Remove duplicates and central movie
        seen_ids = {movie_id}
        unique_candidates = []
        for movie in candidate_movies:
            if movie['id'] not in seen_ids:
                unique_candidates.append(movie)
                seen_ids.add(movie['id'])
        
        # Get detailed information for each candidate and calculate scores
        scored_movies = []
        for candidate in unique_candidates[:30]:  # Limit to 30 for performance
            try:
                candidate_details = get_movie_details(candidate['id'])
                if candidate_details:
                    similarity_score = calculate_similarity_score(central_movie, candidate_details)
                    candidate_details['similarity_score'] = similarity_score
                    scored_movies.append(candidate_details)
            except Exception as e:
                logger.warning(f"Error processing candidate movie {candidate['id']}: {e}")
                continue
        
        # Sort by similarity score and return top results
        scored_movies.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        return scored_movies[:limit]
        
    except Exception as e:
        logger.error(f"Error in enhanced recommendations: {e}")
        return []


# Existing routes
@api_router.get("/")
async def root():
    return {"message": "CinemaMap Movie Recommendation API"}

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
            "api_key": TMDB_API_KEY,
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
    """Get a movie and its related movies using enhanced hybrid algorithm"""
    try:
        # Get the central movie details
        central_movie_data = get_movie_details(movie_id)
        if not central_movie_data:
            raise HTTPException(status_code=404, detail="Movie not found")
        
        # Process central movie with detailed information
        central_movie = process_movie_data(central_movie_data, include_details=True)
        
        # Add director information
        credits = central_movie_data.get('credits', {})
        for crew in credits.get('crew', []):
            if crew.get('job') == 'Director':
                central_movie.director = crew.get('name')
                break
        
        # Add cast information (top 5)
        central_movie.cast = []
        for actor in credits.get('cast', [])[:5]:
            central_movie.cast.append(CastMember(
                id=actor['id'],
                name=actor['name'],
                character=actor.get('character', '')
            ))
        
        # Get enhanced recommendations
        recommended_movies_data = get_enhanced_recommendations(movie_id, 10)
        
        # Process related movies
        related_movies = []
        for movie_data in recommended_movies_data:
            try:
                movie = process_movie_data(movie_data, include_details=True)
                movie.similarity_score = movie_data.get('similarity_score', 0.0)
                
                # Add director
                credits = movie_data.get('credits', {})
                for crew in credits.get('crew', []):
                    if crew.get('job') == 'Director':
                        movie.director = crew.get('name')
                        break
                
                # Add cast (top 3 for related movies)
                movie.cast = []
                for actor in credits.get('cast', [])[:3]:
                    movie.cast.append(CastMember(
                        id=actor['id'],
                        name=actor['name'],
                        character=actor.get('character', '')
                    ))
                
                related_movies.append(movie)
            except Exception as e:
                logger.warning(f"Error processing related movie data: {e}")
                continue
        
        return MovieNetwork(
            central_movie=central_movie,
            related_movies=related_movies
        )
        
    except HTTPException:
        raise
    except requests.RequestException as e:
        logger.error(f"TMDB API error: {e}")
        raise HTTPException(status_code=500, detail="Error fetching movie network data")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/movies/{movie_id}", response_model=Movie)
async def get_movie_details_endpoint(movie_id: int):
    """Get detailed information about a specific movie"""
    try:
        movie_data = get_movie_details(movie_id)
        if not movie_data:
            raise HTTPException(status_code=404, detail="Movie not found")
        
        return process_movie_data(movie_data, include_details=True)
        
    except HTTPException:
        raise
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