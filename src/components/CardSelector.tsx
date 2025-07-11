import React, { useState, useEffect } from 'react';
import { SupportCard } from '../types';
import { dataService } from '../services/dataService';
import SearchInputWithDropdown from './SearchInputWithDropdown';

interface CardSelectorProps {
  selectedCards: (SupportCard | null)[];
  onCardSelect: (card: SupportCard | null, index: number) => void;
  onCardRemove: (index: number) => void;
}

const CardSelector: React.FC<CardSelectorProps> = ({
  selectedCards,
  onCardSelect,
  onCardRemove
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [rarityFilter, setRarityFilter] = useState('');
  const [filteredCards, setFilteredCards] = useState<SupportCard[]>([]);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [rarities, setRarities] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadCards = async () => {
      try {
        setIsLoading(true);
        await dataService.loadAllData();
        const allCards = dataService.getSupportCards();
        const allRarities = dataService.getRarities();
        setFilteredCards(allCards);
        setRarities(allRarities);
        
        // Initialize suggestions with first 10 cards
        const suggestionData = allCards.slice(0, 10).map((card, index) => ({
          id: `card-${index}`,
          title: card.name,
          subtitle: card.rarity,
          imageUrl: card.imageUrl,
          source: 'card',
          sourceName: card.name,
          data: card
        }));
        setSuggestions(suggestionData);
      } catch (error) {
        console.error('Error loading cards:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadCards();
  }, []);

  useEffect(() => {
    const filtered = dataService.searchSupportCards(searchQuery, rarityFilter);
    setFilteredCards(filtered);
    
    // Generate suggestions for dropdown - show all when focused, filtered when searching
    const suggestionResults = searchQuery.length >= 2 
      ? dataService.searchSupportCards(searchQuery, rarityFilter).slice(0, 5)
      : dataService.getSupportCards().slice(0, 10); // Show first 10 when no search
    
    const suggestionData = suggestionResults.map((card, index) => {
      // Count skills and bonds available from this card
      const skillCount = card.trainingEvents.reduce((count, event) => {
        return count + event.choices.filter(choice => choice.skill).length;
      }, 0);
      
      const bondCount = card.trainingEvents.reduce((count, event) => {
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
        id: `card-${index}`,
        title: card.name,
        subtitle: `${card.rarity} | ${card.trainingEvents.length} sự kiện | ${effectsText}`,
        imageUrl: card.imageUrl,
        source: 'card',
        sourceName: card.name,
        data: card
      };
    });
    setSuggestions(suggestionData);
  }, [searchQuery, rarityFilter]);

  const handleSuggestionSelect = (suggestion: any) => {
    if (suggestion.data) {
      // Find first empty slot or replace the last one
      const emptyIndex = selectedCards.findIndex(card => card === null);
      const targetIndex = emptyIndex !== -1 ? emptyIndex : selectedCards.length - 1;
      onCardSelect(suggestion.data, targetIndex);
    }
  };

  const isCardSelected = (card: SupportCard) => {
    return selectedCards.some(selected => selected?.name === card.name);
  };

  const handleCardClick = (card: SupportCard) => {
    if (isCardSelected(card)) {
      // Remove card if already selected
      const index = selectedCards.findIndex(selected => selected?.name === card.name);
      if (index !== -1) {
        onCardRemove(index);
      }
    } else {
      // Add card to first empty slot
      const emptyIndex = selectedCards.findIndex(selected => selected === null);
      if (emptyIndex !== -1) {
        onCardSelect(card, emptyIndex);
      }
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-4">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">Chọn Thẻ Hỗ Trợ</h3>

      <div className="flex gap-4 mb-4">
        <div className="flex-1">
          <SearchInputWithDropdown
            value={searchQuery}
            onChange={setSearchQuery}
            onSuggestionSelect={handleSuggestionSelect}
            suggestions={suggestions}
            showSuggestions={showSuggestions}
            onShowSuggestionsChange={setShowSuggestions}
            placeholder="Tìm kiếm thẻ hỗ trợ..."
          />
        </div>
        <select
          value={rarityFilter}
          onChange={(e) => setRarityFilter(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">Tất cả rarities</option>
          {rarities.map((rarity) => (
            <option key={rarity} value={rarity}>
              {rarity}
            </option>
          ))}
        </select>
      </div>

      {/* Selected Cards Display */}
      <div className="mb-4">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Thẻ đã chọn:</h4>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
          {selectedCards.map((card, index) => (
            <div
              key={index}
              className={`relative border-2 rounded-lg p-2 min-h-[80px] ${
                card ? 'border-green-500 bg-green-50' : 'border-gray-200 bg-gray-50'
              }`}
            >
              {card ? (
                <>
                  <img
                    src={card.imageUrl}
                    alt={card.name}
                    className="w-full h-12 object-cover rounded mb-1"
                  />
                  <p className="text-xs font-medium text-gray-800 truncate">
                    {card.name}
                  </p>
                  <p className="text-xs text-gray-500">{card.rarity}</p>
                  <button
                    onClick={() => onCardRemove(index)}
                    className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs hover:bg-red-600"
                  >
                    ×
                  </button>
                </>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400 text-xs">
                  Trống
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-4">
          <p className="text-gray-500">Đang tải...</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 max-h-60 overflow-y-auto">
          {filteredCards.map((card) => (
            <div
              key={card.name}
              onClick={() => handleCardClick(card)}
              className={`relative cursor-pointer rounded-lg border-2 transition-all hover:shadow-md ${
                isCardSelected(card)
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <img
                src={card.imageUrl}
                alt={card.name}
                className="w-full h-24 object-cover rounded-t-lg"
              />
              <div className="p-2">
                <p className="text-sm font-medium text-gray-800 truncate">
                  {card.name}
                </p>
                <p className="text-xs text-gray-500">{card.rarity}</p>
              </div>
              {isCardSelected(card) && (
                <div className="absolute top-1 right-1 bg-green-500 text-white rounded-full w-5 h-5 flex items-center justify-center">
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

export default CardSelector; 