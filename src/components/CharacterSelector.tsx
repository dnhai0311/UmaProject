import React, { useState, useEffect } from 'react';
import { UmaCharacter } from '../types';
import { dataService } from '../services/dataService';
import SearchInputWithDropdown from './SearchInputWithDropdown';

interface CharacterSelectorProps {
  selectedCharacter: UmaCharacter | null;
  onCharacterSelect: (character: UmaCharacter | null) => void;
}

const CharacterSelector: React.FC<CharacterSelectorProps> = ({
  selectedCharacter,
  onCharacterSelect
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredCharacters, setFilteredCharacters] = useState<UmaCharacter[]>([]);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadCharacters = async () => {
      try {
        setIsLoading(true);
        await dataService.loadAllData();
        const chars = dataService.getUmaCharacters();
        setFilteredCharacters(chars);
        
        // Initialize suggestions with first 10 characters
        const suggestionData = chars.slice(0, 10).map((char, index) => ({
          id: `char-${index}`,
          title: char.name,
          subtitle: char.rarity,
          imageUrl: char.imageUrl,
          source: 'character',
          sourceName: char.name,
          data: char
        }));
        setSuggestions(suggestionData);
      } catch (error) {
        console.error('Error loading characters:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadCharacters();
  }, []);

  useEffect(() => {
    const filtered = dataService.searchUmaCharacters(searchQuery);
    setFilteredCharacters(filtered);
    
    // Update suggestions based on search query
    const suggestionResults = searchQuery.length >= 2 
      ? dataService.searchUmaCharacters(searchQuery).slice(0, 5)
      : dataService.getUmaCharacters().slice(0, 10); // Show first 10 when no search
    
    const suggestionData = suggestionResults.map((char, index) => {
      // Count skills and bonds available from this character
      const skillCount = char.events.reduce((count, event) => {
        return count + event.choices.filter(choice => choice.skill).length;
      }, 0);
      
      const bondCount = char.events.reduce((count, event) => {
        return count + event.choices.filter(choice => choice.bond).length;
      }, 0);
      
      let effectsText = '';
      if (skillCount > 0 && bondCount > 0) {
        effectsText = `${skillCount} kỹ năng, ${bondCount} tình cảm`;
      } else if (skillCount > 0) {
        effectsText = `${skillCount} kỹ năng`;
      } else if (bondCount > 0) {
        effectsText = `${bondCount} tình cảm`;
      } else {
        effectsText = 'Hiệu ứng cơ bản';
      }
      
      return {
        id: `char-${index}`,
        title: char.name,
        subtitle: `${char.rarity} | ${char.events.length} sự kiện | ${effectsText}`,
        imageUrl: char.imageUrl,
        source: 'character',
        sourceName: char.name,
        data: char
      };
    });
    setSuggestions(suggestionData);
  }, [searchQuery]);

  const handleSuggestionSelect = (suggestion: any) => {
    if (suggestion.data) {
      onCharacterSelect(suggestion.data);
    }
  };

  const handleCharacterClick = (character: UmaCharacter) => {
    onCharacterSelect(character);
  };

  const clearSelection = () => {
    onCharacterSelect(null);
    setSearchQuery('');
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800">Chọn Nhân Vật</h3>
        {selectedCharacter && (
          <button
            onClick={clearSelection}
            className="text-sm text-red-500 hover:text-red-700"
          >
            Xóa lựa chọn
          </button>
        )}
      </div>

      <SearchInputWithDropdown
        value={searchQuery}
        onChange={setSearchQuery}
        onSuggestionSelect={handleSuggestionSelect}
        suggestions={suggestions}
        showSuggestions={showSuggestions}
        onShowSuggestionsChange={setShowSuggestions}
        placeholder="Tìm kiếm nhân vật..."
        className="mb-4"
      />

      {isLoading ? (
        <div className="text-center py-4">
          <p className="text-gray-500">Đang tải...</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 max-h-60 overflow-y-auto">
          {filteredCharacters.map((character) => (
            <div
              key={character.name}
              onClick={() => handleCharacterClick(character)}
              className={`relative cursor-pointer rounded-lg border-2 transition-all hover:shadow-md ${
                selectedCharacter?.name === character.name
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <img
                src={character.imageUrl}
                alt={character.name}
                className="w-full h-24 object-cover rounded-t-lg"
              />
              <div className="p-2">
                <p className="text-sm font-medium text-gray-800 truncate">
                  {character.name}
                </p>
                <p className="text-xs text-gray-500">{character.rarity}</p>
              </div>
              {selectedCharacter?.name === character.name && (
                <div className="absolute top-1 right-1 bg-blue-500 text-white rounded-full w-5 h-5 flex items-center justify-center">
                  <span className="text-xs">✓</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CharacterSelector; 