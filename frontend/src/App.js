import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";
import MovieSearch from "./components/MovieSearch";
import MovieNetwork from "./components/MovieNetwork";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [selectedMovie, setSelectedMovie] = useState(null);
  const [networkData, setNetworkData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleMovieSearch = async (movieId) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get(`${API}/movies/${movieId}/network`);
      setNetworkData(response.data);
      setSelectedMovie(response.data.central_movie);
    } catch (err) {
      console.error("Error fetching movie network:", err);
      setError("Failed to load movie network. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleNodeClick = (movieId) => {
    handleMovieSearch(movieId);
  };

  return (
    <div className="App">
      <div className="app-container">
        <header className="app-header">
          <h1 className="app-title">CinemaMap</h1>
          <p className="app-subtitle">Discover movies through intelligent connections</p>
        </header>

        <MovieSearch onMovieSelect={handleMovieSearch} />

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {loading && (
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Analyzing movie connections...</p>
          </div>
        )}

        {networkData && !loading && (
          <MovieNetwork 
            networkData={networkData}
            onNodeClick={handleNodeClick}
          />
        )}

        {!networkData && !loading && (
          <div className="welcome-message">
            <div className="welcome-content">
              <h2>Welcome to CinemaMap</h2>
              <p>Search for any movie to discover its cinematic universe through intelligent connections based on genres, directors, and cast.</p>
              <div className="features">
                <div className="feature">
                  <span className="feature-icon">🎬</span>
                  <span>Smart recommendations</span>
                </div>
                <div className="feature">
                  <span className="feature-icon">🕸️</span>
                  <span>Visual connections</span>
                </div>
                <div className="feature">
                  <span className="feature-icon">🎯</span>
                  <span>Relevant discoveries</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;