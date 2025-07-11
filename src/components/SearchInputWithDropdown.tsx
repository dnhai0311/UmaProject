import React, { useState, useEffect, useRef } from 'react';
import { Search, X } from 'lucide-react';

interface SearchSuggestion {
  id: string;
  title: string;
  subtitle?: string;
  imageUrl?: string;
  source?: string;
  sourceName?: string;
  data?: any;
}

interface SearchInputWithDropdownProps {
  value: string;
  onChange: (value: string) => void;
  onSuggestionSelect?: (suggestion: SearchSuggestion) => void;
  onSearch?: () => void;
  suggestions: SearchSuggestion[];
  placeholder?: string;
  className?: string;
  showSuggestions?: boolean;
  onShowSuggestionsChange?: (show: boolean) => void;
  showAllOnFocus?: boolean;
}

const SearchInputWithDropdown: React.FC<SearchInputWithDropdownProps> = ({
  value,
  onChange,
  onSuggestionSelect,
  onSearch,
  suggestions,
  placeholder = "Search...",
  className = "",
  showSuggestions = false,
  onShowSuggestionsChange,
  showAllOnFocus = true
}) => {
  const [isFocused, setIsFocused] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsFocused(false);
        onShowSuggestionsChange?.(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onShowSuggestionsChange]);

  const handleInputChange = (newValue: string) => {
    onChange(newValue);
    // Always show suggestions when focused, regardless of input length
    if (isFocused) {
      onShowSuggestionsChange?.(true);
    }
  };

  const handleFocus = () => {
    setIsFocused(true);
    if (showAllOnFocus) {
      onShowSuggestionsChange?.(true);
    }
  };

  const handleSuggestionClick = (suggestion: SearchSuggestion) => {
    onChange(suggestion.title);
    onSuggestionSelect?.(suggestion);
    onShowSuggestionsChange?.(false);
    setIsFocused(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      onSearch?.();
      onShowSuggestionsChange?.(false);
    }
  };

  const clearSearch = () => {
    onChange('');
    if (showAllOnFocus && isFocused) {
      onShowSuggestionsChange?.(true);
    } else {
      onShowSuggestionsChange?.(false);
    }
  };

  const getSourceIcon = (source?: string) => {
    switch (source) {
      case 'character': return '👤';
      case 'scenario': return '🎭';
      case 'card': return '🃏';
      case 'skill': return '⚡';
      default: return '📄';
    }
  };

  const getSourceColor = (source?: string) => {
    switch (source) {
      case 'character': return 'bg-blue-100 text-blue-800';
      case 'scenario': return 'bg-purple-100 text-purple-800';
      case 'card': return 'bg-green-100 text-green-800';
      case 'skill': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const shouldShowDropdown = showSuggestions && suggestions.length > 0 && isFocused;

  return (
    <div className={`relative ${className}`} ref={containerRef}>
      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
      <input
        type="text"
        value={value}
        onChange={(e) => handleInputChange(e.target.value)}
        onKeyPress={handleKeyPress}
        onFocus={handleFocus}
        placeholder={placeholder}
        className="w-full pl-10 pr-10 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      />
      {value && (
        <button
          onClick={clearSearch}
          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
        >
          <X className="w-4 h-4" />
        </button>
      )}
      
      {/* Suggestions Dropdown */}
      {shouldShowDropdown && (
        <div className="absolute top-full left-0 right-0 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-60 overflow-y-auto">
          {suggestions.map((suggestion) => (
            <div
              key={suggestion.id}
              onClick={() => handleSuggestionClick(suggestion)}
              className="flex items-center p-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-b-0"
            >
              {suggestion.imageUrl && (
                <img
                  src={suggestion.imageUrl}
                  alt={suggestion.title}
                  className="w-8 h-8 rounded mr-3 object-cover"
                />
              )}
              <div className="flex-1">
                <div className="font-medium text-gray-800">{suggestion.title}</div>
                {suggestion.subtitle && (
                  <div className="text-sm text-gray-600 flex items-center gap-2">
                    {suggestion.source && (
                      <span className={`px-2 py-1 rounded text-xs ${getSourceColor(suggestion.source)}`}>
                        {getSourceIcon(suggestion.source)} {suggestion.sourceName || suggestion.source}
                      </span>
                    )}
                    {suggestion.subtitle}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SearchInputWithDropdown; 