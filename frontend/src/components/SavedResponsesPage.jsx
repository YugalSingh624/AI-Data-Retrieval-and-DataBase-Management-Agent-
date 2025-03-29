// import React, { useState, useEffect } from 'react';
// import { useUser } from '@clerk/clerk-react';
// import ReactMarkdown from 'react-markdown';
// import remarkGfm from 'remark-gfm';

// const API_BASE_URL = 'http://127.0.0.1:5000';

// /**
//  * Utility to format ISO timestamps to a more readable string.
//  * Adjust locale and options as desired.
//  */
// function formatTimestamp(timestamp) {
//   if (!timestamp) return '';
//   const date = new Date(timestamp);
//   const options = {
//     year: 'numeric',
//     month: 'short',  // e.g., "Mar"
//     day: 'numeric',
//     hour: 'numeric',
//     minute: 'numeric',
//     second: 'numeric'
//   };
//   return date.toLocaleString('en-US', options);
// }

// function SavedResponsesPage() {
//   const { user } = useUser();
//   const [responses, setResponses] = useState([]);
//   const [error, setError] = useState(null);

//   // Holds the response that is currently selected (for the modal)
//   const [selectedResponse, setSelectedResponse] = useState(null);

//   useEffect(() => {
//     if (user) {
//       fetchSavedResponses(user.id);
//     }
//   }, [user]);

//   const fetchSavedResponses = async (userId) => {
//     try {
//       const response = await fetch(`${API_BASE_URL}/api/get-stored-responses`, {
//         method: 'POST',
//         headers: {
//           'Content-Type': 'application/json'
//         },
//         body: JSON.stringify({ userId })
//       });

//       if (!response.ok) {
//         throw new Error('Error fetching stored responses');
//       }

//       const data = await response.json();
//       if (data.responses) {
//         setResponses(data.responses);
//       } else {
//         setResponses([]);
//       }
//     } catch (err) {
//       console.error(err);
//       setError('Failed to fetch saved responses.');
//     }
//   };

//   // Opens the modal for a specific response
//   const handleCardClick = (resp) => {
//     setSelectedResponse(resp);
//   };

//   // Closes the modal when clicking on the overlay
//   const handleOverlayClick = () => {
//     setSelectedResponse(null);
//   };

//   // Prevents the modal from closing if we click inside the modal content
//   const handleModalContentClick = (e) => {
//     e.stopPropagation();
//   };

//   // Copies the content of the selected response to clipboard
//   const handleCopyClick = async () => {
//     if (selectedResponse && selectedResponse.content) {
//       try {
//         await navigator.clipboard.writeText(selectedResponse.content);
//         alert('Copied to clipboard!');
//       } catch (error) {
//         console.error('Failed to copy text:', error);
//       }
//     }
//   };

//   return (
//     <div className="saved-responses-container">
//       <h2>Saved Responses</h2>
//       {error && <p className="error-message">{error}</p>}
//       {responses.length === 0 ? (
//         <p>No saved responses found.</p>
//       ) : (
//         <div className="responses-list">
//           {responses.map((resp, index) => (
//             <div
//               className="response-card"
//               key={index}
//               onClick={() => handleCardClick(resp)}
//             >
//               <p><strong>Timestamp:</strong> {formatTimestamp(resp.timestamp)}</p>
//               {resp.searchQuery && (
//                 <p>
//                   <strong>Search Query:</strong> {resp.searchQuery}
//                 </p>
//               )}
//             </div>
//           ))}
//         </div>
//       )}

//       {/* Modal Overlay */}
//       {selectedResponse && (
//         <div className="modal-overlay" onClick={handleOverlayClick}>
//           <div className="modal-content" onClick={handleModalContentClick}>
            
//             {/* Sticky header with close button */}
//             <div className="modal-header">
//               <button
//                 className="close-button"
//                 onClick={() => setSelectedResponse(null)}
//               >
//                 &times;
//               </button>
//             </div>

//             <h3>Full Response</h3>
//             <p><strong>Timestamp:</strong> {formatTimestamp(selectedResponse.timestamp)}</p>
//             {selectedResponse.searchQuery && (
//               <p>
//                 <strong>Search Query:</strong> {selectedResponse.searchQuery}
//               </p>
//             )}
//             <ReactMarkdown remarkPlugins={[remarkGfm]}>
//               {selectedResponse.content}
//             </ReactMarkdown>

//             <div className="modal-buttons">
//               <button onClick={handleCopyClick}>Copy</button>
//             </div>
//           </div>
//         </div>
//       )}
//     </div>
//   );
// }

// export default SavedResponsesPage;




import React, { useState, useEffect } from 'react';
import { useUser } from '@clerk/clerk-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const API_BASE_URL = 'http://127.0.0.1:5000';

/**
 * Utility to format ISO timestamps to a more readable string.
 * Adjust locale and options as desired.
 */
function formatTimestamp(timestamp) {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  const options = {
    year: 'numeric',
    month: 'short',  // e.g., "Mar"
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
    second: 'numeric'
  };
  return date.toLocaleString('en-US', options);
}

function SavedResponsesPage() {
  const { user } = useUser();
  const [responses, setResponses] = useState([]);
  const [error, setError] = useState(null);
  // Holds the response that is currently selected (for the modal)
  const [selectedResponse, setSelectedResponse] = useState(null);

  useEffect(() => {
    if (user) {
      fetchSavedResponses(user.id);
    }
  }, [user]);

  const fetchSavedResponses = async (userId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/get-stored-responses`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ userId })
      });

      if (!response.ok) {
        throw new Error('Error fetching stored responses');
      }

      const data = await response.json();
      if (data.responses) {
        setResponses(data.responses);
      } else {
        setResponses([]);
      }
    } catch (err) {
      console.error(err);
      setError('Failed to fetch saved responses.');
    }
  };

  // Opens the modal for a specific response
  const handleCardClick = (resp) => {
    setSelectedResponse(resp);
  };

  // Closes the modal when clicking on the overlay
  const handleOverlayClick = () => {
    setSelectedResponse(null);
  };

  // Prevents the modal from closing if we click inside the modal content
  const handleModalContentClick = (e) => {
    e.stopPropagation();
  };

  // Copies the content of the selected response to clipboard
  const handleCopyClick = async () => {
    if (selectedResponse && selectedResponse.content) {
      try {
        await navigator.clipboard.writeText(selectedResponse.content);
        alert('Copied to clipboard!');
      } catch (error) {
        console.error('Failed to copy text:', error);
      }
    }
  };

  // Deletes a response by making a DELETE request to the backend
// First, add this console.log to see what's actually being sent
const handleDelete = async (responseId, e) => {
  e.stopPropagation();
  if (!window.confirm('Are you sure you want to delete this response?')) {
    return;
  }
  
  console.log("Attempting to delete response with ID:", responseId);
  
  try {
    const res = await fetch(`${API_BASE_URL}/api/delete-response`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ responseId }),
    });

    console.log("Delete response status:", res.status);
    
    if (res.ok) {
      setResponses((prev) => prev.filter((r) => r._id !== responseId));
    } else {
      const errorData = await res.json();
      console.error("Delete error:", errorData);
      alert('Failed to delete response: ' + (errorData.error || 'Unknown error'));
    }
  } catch (err) {
    console.error(err);
    alert('An error occurred while deleting.');
  }
};
  

  return (
    <div className="saved-responses-container">
      <h2>Saved Responses</h2>
      {error && <p className="error-message">{error}</p>}
      {responses.length === 0 ? (
        <p>No saved responses found.</p>
      ) : (
        <div className="responses-list">
          {responses.map((resp, index) => (
            <div
              className="response-card"
              key={index}
              onClick={() => handleCardClick(resp)}
            >
              <div className="card-content">
                <p><strong>Timestamp:</strong> {formatTimestamp(resp.timestamp)}</p>
                {resp.searchQuery && (
                  <p>
                    <strong>Search Query:</strong> {resp.searchQuery}
                  </p>
                )}
              </div>
              <button
                className="delete-button"
                onClick={(e) => handleDelete(resp._id, e)}
                title="Delete response"
              >
                🗑️
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Modal Overlay */}
      {selectedResponse && (
        <div className="modal-overlay" onClick={handleOverlayClick}>
          <div className="modal-content" onClick={handleModalContentClick}>
            
            {/* Sticky header with close button */}
            <div className="modal-header">
              <button
                className="close-button"
                onClick={() => setSelectedResponse(null)}
              >
                &times;
              </button>
            </div>

            <h3>Full Response</h3>
            <p><strong>Timestamp:</strong> {formatTimestamp(selectedResponse.timestamp)}</p>
            {selectedResponse.searchQuery && (
              <p>
                <strong>Search Query:</strong> {selectedResponse.searchQuery}
              </p>
            )}
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {selectedResponse.content}
            </ReactMarkdown>

            <div className="modal-buttons">
              <button onClick={handleCopyClick}>Copy</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SavedResponsesPage;
