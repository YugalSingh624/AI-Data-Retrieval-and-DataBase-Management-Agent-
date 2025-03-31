import React, { useState } from 'react';
import { Search } from 'lucide-react';

function SearchBar({ onSearch, isLoading }) {
  const [searchQuery, setSearchQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (searchQuery.trim() && !isLoading) {
      onSearch(searchQuery);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="search-wrapper">
      <input
        type="text"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        placeholder="Ask me anything..."
        className="search-input"
        disabled={isLoading}
      />
      <button 
        type="submit" 
        className="search-button"
        disabled={isLoading || !searchQuery.trim()}
      >
        <Search size={20} />
        <span>Search</span>
      </button>
    </form>
  );
}

export default SearchBar