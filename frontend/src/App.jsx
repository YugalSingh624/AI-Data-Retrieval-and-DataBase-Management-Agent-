// File: App.jsx
import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './App.css';
import SearchBar from './components/SearchBar';
import ResponseArea from './components/ResponseArea';
import ToolCallsViewer from './components/ToolCallsViewer';
import LoadingIndicator from './components/LoadingIndicator';
import SavedResponsesPage from './components/SavedResponsesPage';
import { SignedIn, SignedOut, SignInButton, UserButton, useUser } from "@clerk/clerk-react";

// Base URL for the Flask backend
const API_BASE_URL = 'http://127.0.0.1:5000';

function App() {
  const [query, setQuery] = useState('');
  const [cleanedResponse, setCleanedResponse] = useState('');
  const [toolCalls, setToolCalls] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const eventSourceRef = useRef(null);

  const { user } = useUser();

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

  // Check server connection on mount
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

  // Sync user data with backend
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
    // Wrap the entire application in a Router
    <Router>
      <div className="app-container">
        <header>
          <div className="auth-buttons">
            <SignedOut>
              <SignInButton className="cl-signIn-button" />
            </SignedOut>
            <SignedIn>
              <UserButton className="cl-user-button" />
            </SignedIn>
          </div>
          <h1>AI Search Assistant</h1>
          <p>Powered by multiple search engines and web scraping</p>

          {/* Simple navigation to switch between home and saved responses */}
          <nav>
            <Link to="/" style={{ marginRight: '10px' }}>Home</Link>
            <Link to="/saved-responses">Saved Responses</Link>
          </nav>
        </header>

        {/* Define Routes for "/" and "/saved-responses" */}
        <Routes>
          {/* Home route ("/") renders your existing main content */}
          <Route
            path="/"
            element={
              <main>
                <SearchBar onSearch={handleSearch} isLoading={isLoading} />
                {isLoading && <LoadingIndicator />}
                {error && (
                  <div className="error-message">
                    <p>{error}</p>
                  </div>
                )}
                <div className="content-container">
                  {/* Pass the original search query to ResponseArea */}
                  <ResponseArea response={cleanedResponse} isFinalResponse={true} searchQuery={query} />
                  {toolCalls.length > 0 && <ToolCallsViewer toolCalls={toolCalls} />}
                </div>
              </main>
            }
          />

          {/* Route for "/saved-responses" */}
          <Route
            path="/saved-responses"
            element={<SavedResponsesPage />}
          />
        </Routes>

        <footer>
          <p>Using Flask backend with multiple AI-powered search agents</p>
          <p>Connected to: {API_BASE_URL}</p>
        </footer>
      </div>
    </Router>
  );
}

export default App;
