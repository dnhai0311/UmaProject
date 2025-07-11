import React, { useState, useEffect } from 'react';
import { Scenario } from '../types';
import { dataService } from '../services/dataService';
import SearchInputWithDropdown from './SearchInputWithDropdown';

interface ScenarioSelectorProps {
  selectedScenario: Scenario | null;
  onScenarioSelect: (scenario: Scenario | null) => void;
}

const ScenarioSelector: React.FC<ScenarioSelectorProps> = ({
  selectedScenario,
  onScenarioSelect
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredScenarios, setFilteredScenarios] = useState<Scenario[]>([]);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadScenarios = async () => {
      try {
        setIsLoading(true);
        await dataService.loadAllData();
        const scens = dataService.getScenarios();
        setFilteredScenarios(scens);
        
        // Initialize suggestions with first 10 scenarios
        const suggestionData = scens.slice(0, 10).map((scenario, index) => ({
          id: `scenario-${index}`,
          title: scenario.name,
          subtitle: `${scenario.events.length} sự kiện`,
          imageUrl: scenario.imageUrl,
          source: 'scenario',
          sourceName: scenario.name,
          data: scenario
        }));
        setSuggestions(suggestionData);
      } catch (error) {
        console.error('Error loading scenarios:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadScenarios();
  }, []);

  useEffect(() => {
    const filtered = dataService.searchScenarios(searchQuery);
    setFilteredScenarios(filtered);
    
    // Generate suggestions for dropdown - show all when focused, filtered when searching
    const suggestionResults = searchQuery.length >= 2 
      ? dataService.searchScenarios(searchQuery).slice(0, 5)
      : dataService.getScenarios().slice(0, 10); // Show first 10 when no search
    
    const suggestionData = suggestionResults.map((scenario, index) => {
      // Count skills and bonds available in this scenario
      const skillCount = scenario.events.reduce((count, event) => {
        return count + event.choices.filter(choice => choice.skill).length;
      }, 0);
      
      const bondCount = scenario.events.reduce((count, event) => {
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
        id: `scenario-${index}`,
        title: scenario.name,
        subtitle: `${scenario.events.length} sự kiện | ${effectsText}`,
        imageUrl: scenario.imageUrl,
        source: 'scenario',
        sourceName: scenario.name,
        data: scenario
      };
    });
    setSuggestions(suggestionData);
  }, [searchQuery]);

  const handleSuggestionSelect = (suggestion: any) => {
    if (suggestion.data) {
      onScenarioSelect(suggestion.data);
    }
  };

  const handleScenarioClick = (scenario: Scenario) => {
    onScenarioSelect(scenario);
  };

  const clearSelection = () => {
    onScenarioSelect(null);
    setSearchQuery('');
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800">Chọn Kịch Bản</h3>
        {selectedScenario && (
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
        placeholder="Tìm kiếm kịch bản..."
        className="mb-4"
      />

      {isLoading ? (
        <div className="text-center py-4">
          <p className="text-gray-500">Đang tải...</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 max-h-60 overflow-y-auto">
          {filteredScenarios.map((scenario) => (
            <div
              key={scenario.name}
              onClick={() => handleScenarioClick(scenario)}
              className={`relative cursor-pointer rounded-lg border-2 transition-all hover:shadow-md ${
                selectedScenario?.name === scenario.name
                  ? 'border-purple-500 bg-purple-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              {scenario.imageUrl ? (
                <img
                  src={scenario.imageUrl}
                  alt={scenario.name}
                  className="w-full h-24 object-cover rounded-t-lg"
                />
              ) : (
                <div className="w-full h-24 bg-gray-200 rounded-t-lg flex items-center justify-center">
                  <span className="text-gray-500 text-sm">🎭</span>
                </div>
              )}
              <div className="p-2">
                <p className="text-sm font-medium text-gray-800 truncate">
                  {scenario.name}
                </p>
                <p className="text-xs text-gray-500">{scenario.events.length} sự kiện</p>
              </div>
              {selectedScenario?.name === scenario.name && (
                <div className="absolute top-1 right-1 bg-purple-500 text-white rounded-full w-5 h-5 flex items-center justify-center">
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

export default ScenarioSelector; 