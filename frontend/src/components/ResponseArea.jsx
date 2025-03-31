// File: components/ResponseArea.jsx
import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useUser } from '@clerk/clerk-react';
import rehypeRaw from "rehype-raw";


const API_BASE_URL = 'http://127.0.0.1:5000';

function ResponseArea({ response, isFinalResponse, searchQuery }) {
  const [displayResponse, setDisplayResponse] = useState('');
  const [isStorageEnabled, setIsStorageEnabled] = useState(false);

  const { isSignedIn, user } = useUser();

  useEffect(() => {
    // Only set response if it's the final, cleaned response
    if (response && isFinalResponse) {
      setDisplayResponse(response);
      // Enable storage button when final response is received and user is signed in
      setIsStorageEnabled(!!response && isSignedIn);
    }
  }, [response, isFinalResponse, isSignedIn]);

  const handleSubmit = async () => {
    // Validate before submission
    if (!isSignedIn) {
      alert("Please sign in to store search results.");
      return;
    }

    if (!displayResponse) {
      alert("No response to store.");
      return;
    }

    // Include searchQuery along with the other fields.
    const dataToPush = {
      content: displayResponse,
      userId: user.id,
      searchQuery: searchQuery, // Sending the original search query to backend
      timestamp: new Date().toISOString()
    };

    try {
      const res = await fetch(`${API_BASE_URL}/api/pushData`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(dataToPush),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Failed to store search results");
      }

      // Success feedback
      alert("Search results stored successfully!");
    } catch (error) {
      console.error("Error storing search results:", error);
      alert(`Failed to store results: ${error.message}`);
    }
  };

  // Don't render if no final response
  if (!displayResponse) return null;

  return (
    <div className="response-area">
      <div className="response-header">
        <h2>AI Response</h2>
        <button 
          className={`dbbutton ${isStorageEnabled ? 'enabled' : 'disabled'}`}
          onClick={handleSubmit}
        >
          Store Search Results
        </button>
      </div>
      <div className="markdown-content">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeRaw]} // Allows raw HTML inside Markdown
          components={{
            a: ({ node, ...props }) => (
              <a target="_blank" rel="noopener noreferrer" {...props} />
            ),
          }}
        >
          {displayResponse}
        </ReactMarkdown>
      </div>
    </div>
  );
}

export default ResponseArea;