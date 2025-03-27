// File: components/ToolCallsViewer.jsx
import React, { useState } from 'react';

function ToolCallsViewer({ toolCalls }) {
  const [expanded, setExpanded] = useState({});

  const toggleExpand = (index) => {
    setExpanded(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  return (
    <div className="tool-calls-viewer">
      <h2>Search Operations ({toolCalls.length})</h2>
      <div className="tool-calls-list">
        {toolCalls.map((call, index) => (
          <div 
            key={index} 
            className={`tool-call-item ${expanded[index] ? 'expanded' : ''}`}
          >
            <div 
              className="tool-call-header" 
              onClick={() => toggleExpand(index)}
            >
              <span className="tool-name">{call.name || 'Unknown Tool'}</span>
              <span className="tool-action">{call.input?.action || call.action || 'Unknown Action'}</span>
              <span className="expand-icon">{expanded[index] ? '▼' : '►'}</span>
            </div>
            
            {expanded[index] && (
              <div className="tool-call-details">
                <pre>{JSON.stringify(call.input || call, null, 2)}</pre>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default ToolCallsViewer;