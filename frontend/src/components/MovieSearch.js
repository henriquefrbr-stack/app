import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./MovieSearch.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const MovieSearch = ({ onMovieSelect }) => {
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [showResults, setShowResults] = useState(false);
  const [loading, setLoading] = useState(false);
  const searchRef = useRef(null);

  const handleSearch = async (searchQuery) => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }

    setLoading(true);
    try {
      const response = await axios.get(`${API}/movies/search`, {
        params: { query: searchQuery }
      });
      setSearchResults(response.data.results.slice(0, 8)); // Limit to 8 results
      setShowResults(true);
    } catch (error) {
      console.error("Error searching movies:", error);
      setSearchResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const value = e.target.value;
    setQuery(value);
    
    // Debounce search
    if (value.trim()) {
      const timeoutId = setTimeout(() => handleSearch(value), 300);
      return () => clearTimeout(timeoutId);
    } else {
      setShowResults(false);
    }
  };

  const handleMovieClick = (movie) => {
    setQuery(movie.title);
    setShowResults(false);
    onMovieSelect(movie.id);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (searchResults.length > 0) {
      handleMovieClick(searchResults[0]);
    }
  };

  // Close results when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setShowResults(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="movie-search" ref={searchRef}>
      <form onSubmit={handleSubmit} className="search-form">
        <div className="search-input-container">
          <input
            type="text"
            value={query}
            onChange={handleInputChange}
            placeholder="Search for a movie..."
            className="search-input"
            autoComplete="off"
          />
          <button type="submit" className="search-button">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"></circle>
              <path d="21 21l-4.35-4.35"></path>
            </svg>
          </button>
        </div>
      </form>

      {showResults && (
        <div className="search-results">
          {loading ? (
            <div className="search-loading">
              <div className="search-spinner"></div>
              <span>Searching...</span>
            </div>
          ) : (
            <>
              {searchResults.length > 0 ? (
                <div className="results-list">
                  {searchResults.map((movie) => (
                    <div
                      key={movie.id}
                      className="result-item"
                      onClick={() => handleMovieClick(movie)}
                    >
                      <div className="result-poster">
                        {movie.poster_url ? (
                          <img src={movie.poster_url} alt={movie.title} />
                        ) : (
                          <div className="poster-placeholder">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                              <path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z"/>
                            </svg>
                          </div>
                        )}
                      </div>
                      <div className="result-info">
                        <h3 className="result-title">{movie.title}</h3>
                        <p className="result-year">
                          {movie.release_date ? new Date(movie.release_date).getFullYear() : 'N/A'}
                        </p>
                        <div className="result-rating">
                          <span className="rating-star">⭐</span>
                          <span>{movie.vote_average ? movie.vote_average.toFixed(1) : 'N/A'}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="no-results">
                  <p>No movies found for "{query}"</p>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default MovieSearch;