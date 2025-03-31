import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Search, Bot, Home, BookMarked, DollarSign, Sun, Moon } from 'lucide-react';
import { SignedIn, SignedOut, SignInButton, UserButton, useUser } from "@clerk/clerk-react";
import './App.css';
import SearchBar from './components/SearchBar';
import ResponseArea from './components/ResponseArea';
import ToolCallsViewer from './components/ToolCallsViewer';
import LoadingIndicator from './components/LoadingIndicator';
import SavedResponsesPage from './components/SavedResponsesPage';

const API_BASE_URL = 'http://127.0.0.1:5000';

function App() {
  const [query, setQuery] = useState('');
  const [cleanedResponse, setCleanedResponse] = useState('');
  const [toolCalls, setToolCalls] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const eventSourceRef = useRef(null);
  const { user } = useUser();

  // Initialize theme from localStorage
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    setIsDarkMode(savedTheme === 'dark');
  }, []);

  // Update theme in localStorage and body class
  useEffect(() => {
    document.body.className = isDarkMode ? 'dark-mode' : 'light-mode';
    localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
  }, [isDarkMode]);

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
  };

  const handleSearch = async (searchQuery) => {
    setQuery(searchQuery);
    setCleanedResponse('');
    setToolCalls([]);
    setError(null);
    setIsLoading(true);

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const encodedQuery = encodeURIComponent(searchQuery);
      eventSourceRef.current = new EventSource(`${API_BASE_URL}/api/stream?query=${encodedQuery}`);

      eventSourceRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("Received Cleaned data:", data);
      
          if (data.chunk) {
            setCleanedResponse((prev) => prev + (data.chunk || ''));
          } else if (data.tool_call) {
            setToolCalls((prev) => [...prev, data.tool_call]);
          } else if (data.done) {
            setIsLoading(false);
            eventSourceRef.current.close();
          } else if (data.error) {
            setError(data.error);
            setIsLoading(false);
            eventSourceRef.current.close();
          }
        } catch (jsonError) {
          console.error('Error parsing response:', jsonError);
          setError(`Error parsing response: ${jsonError.message}`);
          setIsLoading(false);
        }
      };

      eventSourceRef.current.onerror = (e) => {
        console.error('EventSource error:', e);
        setError('Connection error with the server. Please check if the Flask backend is running at http://127.0.0.1:5000');
        setIsLoading(false);
        eventSourceRef.current.close();
      };
    } catch (err) {
      console.error('Error setting up EventSource:', err);
      setError(`Error connecting to the server: ${err.message}`);
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const checkServerConnection = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/stream`, { 
          method: 'GET',
          headers: {
            'Accept': 'application/json',
          },
        });
        
        if (!response.ok) {
          console.warn('Backend server may not be available:', response.status);
        } else {
          console.log('Connected to Flask backend successfully');
        }
      } catch (err) {
        console.warn('Could not connect to Flask backend:', err);
      }
    };

    checkServerConnection();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  useEffect(() => {
    const syncUserToBackend = async () => {
      if (user) {
        try {
          const response = await fetch(`${API_BASE_URL}/api/sync-user`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              clerkId: user.id,
              email: user.primaryEmailAddress?.emailAddress,
              name: `${user.firstName || ''} ${user.lastName || ''}`.trim(),
              imageUrl: user.imageUrl
            })
          });

          if (!response.ok) {
            console.error('Failed to sync user to backend');
          }
        } catch (error) {
          console.error('Error syncing user:', error);
        }
      }
    };

    syncUserToBackend();
  }, [user]);

  return (
    <Router>
      <div className={`app-container ${isDarkMode ? 'dark-mode' : 'light-mode'}`}>
        <nav className="navbar">
          <div className="navbar-container">
            <div className="navbar-content">
              <div className="navbar-brand">
                <Bot className="brand-icon" size={32} />
                <span className="brand-text">AI Search Assistant</span>
              </div>
              <div className="navbar-links">
                <Link to="/" className="nav-link">
                  <Home size={20} />
                  <span>Home</span>
                </Link>
                <Link to="/saved-responses" className="nav-link">
                  <BookMarked size={20} />
                  <span>Saved</span>
                </Link>
                <button className="theme-toggle" onClick={toggleTheme}>
                  {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
                  <span>{isDarkMode ? 'Light Mode' : 'Dark Mode'}</span>
                </button>
                <div className="auth-buttons">
                  <SignedOut>
                    <SignInButton className="cl-signIn-button" />
                  </SignedOut>
                  <SignedIn>
                    <UserButton className="cl-user-button" />
                  </SignedIn>
                </div>
                <button className="upgrade-button">
                  <DollarSign size={16} />
                  <span>Upgrade</span>
                </button>
              </div>
            </div>
          </div>
        </nav>

        <Routes>
          <Route
            path="/"
            element={
              <main className="main-content">
                <div className="hero">
                  <h1 className="hero-title">Your AI-Powered Search Assistant</h1>
                  <p className="hero-subtitle">
                    Powered by multiple search engines and web scraping technology to provide comprehensive results
                  </p>
                </div>

                <div className="search-container">
                  <SearchBar onSearch={handleSearch} isLoading={isLoading} />
                </div>

                {isLoading && <LoadingIndicator />}
                
                {error && (
                  <div className="error-message">
                    <p>{error}</p>
                  </div>
                )}

                <div className="content-container">
                  <ResponseArea response={cleanedResponse} isFinalResponse={true} searchQuery={query} />
                  {toolCalls.length > 0 && <ToolCallsViewer toolCalls={toolCalls} />}
                </div>

                <div className="status-container">
                  <div className="status-content">
                    <div className="status-item">
                      <div className="status-dot"></div>
                      <span>Using Flask backend with multiple AI-powered search agents</span>
                    </div>
                    <div className="status-item">
                      <div className="status-dot"></div>
                      <span>Connected to: {API_BASE_URL}</span>
                    </div>
                  </div>
                </div>
              </main>
            }
          />

          <Route
            path="/saved-responses"
            element={<SavedResponsesPage />}
          />
        </Routes>

        <footer className="footer">
          <p>&copy; 2025 AI Search Assistant. All rights reserved.</p>
        </footer>
      </div>
    </Router>
  );
}

export default App;