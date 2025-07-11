import React, { useState, useEffect } from 'react';
import { UmaCharacter, Scenario, SupportCard, Event } from '../types';
import { dataService } from '../services/dataService';
import SearchInputWithDropdown from './SearchInputWithDropdown';

interface EventDisplayProps {
  character: UmaCharacter | null;
  scenario: Scenario | null;
  cards: SupportCard[];
}

interface SearchResult {
  id: string;
  title: string;
  content: string;
  source: string;
  sourceName: string;
  sourceImage?: string;
  event?: any;
}

const EventDisplay: React.FC<EventDisplayProps> = ({
  character,
  scenario,
  cards
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);
  const [showOnlySelected, setShowOnlySelected] = useState(true); // Default to true - show only selected when items are selected

  // Check if any items are selected
  const hasSelectedItems = character || scenario || cards.length > 0;

  useEffect(() => {
    const loadData = async () => {
      try {
        await dataService.loadAllData();
      } catch (error) {
        console.error('Error loading data:', error);
      }
    };
    loadData();
  }, []);

  useEffect(() => {
    // Generate suggestions for dropdown - show all when focused, filtered when searching
    let suggestionResults: any[] = [];
    
    const eventResults = searchQuery.length >= 2 
      ? dataService.searchEvents(searchQuery).slice(0, 5)
      : dataService.searchEvents('').slice(0, 10); // Show first 10 when no search
    
    suggestionResults = eventResults.map((result, index) => {
      // Get choice count and effects
      const choiceCount = result.event.choices?.length || 0;
      const hasSkills = result.event.choices?.some((choice: any) => choice.skill) || false;
      const hasBonds = result.event.choices?.some((choice: any) => choice.bond) || false;
      
      let effectsText = '';
      if (hasSkills && hasBonds) {
        effectsText = 'Kỹ năng + Tình cảm';
      } else if (hasSkills) {
        effectsText = 'Có kỹ năng';
      } else if (hasBonds) {
        effectsText = 'Có tình cảm';
      } else {
        effectsText = 'Hiệu ứng cơ bản';
      }
      
      return {
        id: `event-${index}`,
        title: result.event.event.substring(0, 50) + (result.event.event.length > 50 ? '...' : ''),
        subtitle: `${result.sourceName} | ${choiceCount} lựa chọn | ${effectsText}`,
        imageUrl: result.sourceImage,
        source: result.source,
        sourceName: result.sourceName,
        data: result
      };
    });
    
    setSuggestions(suggestionResults);
  }, [searchQuery]);

  const handleSuggestionSelect = (suggestion: any) => {
    if (suggestion.data) {
      setSelectedResult({
        id: suggestion.id,
        title: suggestion.data.event.event,
        content: suggestion.data.sourceName,
        source: suggestion.data.source,
        sourceName: suggestion.data.sourceName,
        sourceImage: suggestion.data.sourceImage,
        event: suggestion.data.event
      });
      setSearchQuery(suggestion.data.event.event);
    }
  };

  const allEvents: Array<{ source: string; events: Event[] }> = [];

  // Always add all events from data service when nothing is selected
  if (!hasSelectedItems) {
    // Load all events from data service
    const allCharacters = dataService.getUmaCharacters();
    const allScenarios = dataService.getScenarios();
    const allCards = dataService.getSupportCards();

    allCharacters.forEach(char => {
      allEvents.push({
        source: `Nhân vật: ${char.name}`,
        events: char.events
      });
    });

    allScenarios.forEach(scen => {
      allEvents.push({
        source: `Kịch bản: ${scen.name}`,
        events: scen.events
      });
    });

    allCards.forEach(card => {
      allEvents.push({
        source: `Thẻ hỗ trợ: ${card.name}`,
        events: card.trainingEvents
      });
    });
  } else {
    // Add events from selected items
    if (character) {
      allEvents.push({
        source: `Nhân vật: ${character.name}`,
        events: character.events
      });
    }

    if (scenario) {
      allEvents.push({
        source: `Kịch bản: ${scenario.name}`,
        events: scenario.events
      });
    }

    cards.forEach(card => {
      allEvents.push({
        source: `Thẻ hỗ trợ: ${card.name}`,
        events: card.trainingEvents
      });
    });
  }

  // Filter events based on checkbox - when checked, only show events from selected items
  const filteredEvents = hasSelectedItems && showOnlySelected
    ? allEvents.filter(eventGroup => {
        // If checkbox is checked and we have selected items, only show events from selected items
        if (character && eventGroup.source.includes(character.name)) return true;
        if (scenario && eventGroup.source.includes(scenario.name)) return true;
        if (cards.some(card => card && eventGroup.source.includes(card.name))) return true;
        return false;
      })
    : allEvents; // Show all events when checkbox is unchecked or no items selected

  if (filteredEvents.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold mb-4 text-gray-800">Sự Kiện</h2>
        <p className="text-gray-600">
          {hasSelectedItems && showOnlySelected
            ? "Không có sự kiện nào từ các items đã chọn."
            : "Đang tải dữ liệu sự kiện..."
          }
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold mb-4 text-gray-800">Tất Cả Sự Kiện</h2>
      
      {/* Search Section */}
      <div className="mb-6">
        <div className="flex items-center gap-4 mb-4">
          <div className="flex-1">
            <SearchInputWithDropdown
              value={searchQuery}
              onChange={setSearchQuery}
              onSuggestionSelect={handleSuggestionSelect}
              suggestions={suggestions}
              showSuggestions={showSuggestions}
              onShowSuggestionsChange={setShowSuggestions}
              placeholder="Tìm kiếm sự kiện hoặc lựa chọn..."
            />
          </div>
          {hasSelectedItems && (
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={showOnlySelected}
                onChange={(e) => setShowOnlySelected(e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              {showOnlySelected ? "Chỉ hiển thị sự kiện đã chọn" : "Hiển thị tất cả sự kiện"}
            </label>
          )}
        </div>

        {/* Selected Result Details */}
        {selectedResult && (
          <div className="bg-blue-50 rounded-lg p-4 mb-4">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-lg font-semibold text-gray-800">Chi tiết</h3>
              <button
                onClick={() => setSelectedResult(null)}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>
            
            <div className="space-y-3">
              {selectedResult.event && (
                <div>
                  <h4 className="font-medium text-gray-800 mb-2">Sự kiện:</h4>
                  <p className="text-gray-700 mb-3">{selectedResult.event.event}</p>
                  
                  {selectedResult.event.choices && selectedResult.event.choices.length > 0 && (
                    <div>
                      <h5 className="font-medium text-gray-800 mb-2">Các lựa chọn:</h5>
                      <div className="space-y-2">
                        {selectedResult.event.choices.map((choice: any, index: number) => (
                          <div key={index} className="bg-white p-3 rounded border">
                            <p className="font-medium text-gray-800 mb-1">{choice.choice}</p>
                            <p className="text-sm text-gray-700">{choice.effect}</p>
                            {choice.skill && (
                              <div className="mt-2 p-2 bg-blue-50 rounded">
                                <p className="text-sm font-medium text-blue-800">Kỹ năng: {choice.skill.name}</p>
                                <p className="text-xs text-blue-700">{choice.skill.effect}</p>
                              </div>
                            )}
                            {choice.bond && (
                              <div className="mt-2 p-2 bg-green-50 rounded">
                                <p className="text-sm font-medium text-green-800">Tình cảm: {choice.bond.name}</p>
                                <p className="text-xs text-green-700">{choice.bond.effect}</p>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      
      <div className="space-y-6">
        {filteredEvents.map((sourceEvents, sourceIndex) => (
          <div key={sourceIndex} className="border-b border-gray-200 pb-6 last:border-b-0">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">{sourceEvents.source}</h3>
            
            <div className="space-y-4">
              {sourceEvents.events.map((event, eventIndex) => (
                <div key={eventIndex} className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-medium text-gray-800 mb-3">{event.event}</h4>
                  
                  <div className="space-y-2">
                    {event.choices.map((choice, choiceIndex) => (
                      <div key={choiceIndex} className="bg-white rounded border border-gray-200 p-3">
                        <div className="font-medium text-blue-600 mb-1">{choice.choice}</div>
                        
                        {choice.effect && (
                          <div className="text-sm text-gray-700 mb-2">
                            <span className="font-medium">Hiệu ứng:</span> {choice.effect}
                          </div>
                        )}
                        
                        {choice.skill && (
                          <div className="text-sm text-green-700 mb-2">
                            <span className="font-medium">Kỹ năng:</span> {choice.skill.name} - {choice.skill.effect}
                          </div>
                        )}
                        
                        {choice.bond && (
                          <div className="text-sm text-purple-700">
                            <span className="font-medium">Mối quan hệ:</span> {choice.bond.name} {choice.bond.effect}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default EventDisplay; 