import React, { useState, useEffect, useCallback } from 'react';
import { Skill, UmaCharacter, Scenario, SupportCard } from '../types';
import { dataService } from '../services/dataService';
import SearchInputWithDropdown from './SearchInputWithDropdown';

interface SkillsTabProps {
  selectedCharacter?: UmaCharacter | null;
  selectedScenario?: Scenario | null;
  selectedCards?: (SupportCard | null)[];
}

const SkillsTab: React.FC<SkillsTabProps> = ({
  selectedCharacter,
  selectedScenario,
  selectedCards = []
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredSkills, setFilteredSkills] = useState<Skill[]>([]);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [showOnlySelected, setShowOnlySelected] = useState(true); // Default to true - show only selected when items are selected

  // Check if any items are selected
  const hasSelectedItems = selectedCharacter || selectedScenario || selectedCards.some(card => card !== null);

  // Function to get event sources for a skill
  const getSkillEventSources = useCallback((skillName: string): Array<{
    source: string;
    sourceName: string;
    event: string;
    choice: string;
  }> => {
    const sources: Array<{
      source: string;
      sourceName: string;
      event: string;
      choice: string;
    }> = [];

    // Check character events
    if (selectedCharacter) {
      selectedCharacter.events.forEach(event => {
        event.choices.forEach(choice => {
          if (choice.skill && choice.skill.name === skillName) {
            sources.push({
              source: 'character',
              sourceName: selectedCharacter.name,
              event: event.event,
              choice: choice.choice
            });
          }
        });
      });
    }

    // Check scenario events
    if (selectedScenario) {
      selectedScenario.events.forEach(event => {
        event.choices.forEach(choice => {
          if (choice.skill && choice.skill.name === skillName) {
            sources.push({
              source: 'scenario',
              sourceName: selectedScenario.name,
              event: event.event,
              choice: choice.choice
            });
          }
        });
      });
    }

    // Check card events
    selectedCards.forEach(card => {
      if (card) {
        card.trainingEvents.forEach(event => {
          event.choices.forEach(choice => {
            if (choice.skill && choice.skill.name === skillName) {
              sources.push({
                source: 'card',
                sourceName: card.name,
                event: event.event,
                choice: choice.choice
              });
            }
          });
        });
      }
    });

    return sources;
  }, [selectedCharacter, selectedScenario, selectedCards]);

  // Combined loading and filtering effect
  useEffect(() => {
    const loadAndFilterSkills = async () => {
      try {
        setIsLoading(true);
        await dataService.loadAllData();
        
        let skills = dataService.searchSkills(searchQuery);
        
        // Filter skills based on checkbox and whether items are selected
        if (hasSelectedItems && showOnlySelected) {
          const selectedSkillNames = new Set<string>();
          
          // Get skills from selected character
          if (selectedCharacter) {
            selectedCharacter.events.forEach(event => {
              event.choices.forEach(choice => {
                if (choice.skill) {
                  selectedSkillNames.add(choice.skill.name);
                }
              });
            });
          }
          
          // Get skills from selected scenario
          if (selectedScenario) {
            selectedScenario.events.forEach(event => {
              event.choices.forEach(choice => {
                if (choice.skill) {
                  selectedSkillNames.add(choice.skill.name);
                }
              });
            });
          }
          
          // Get skills from selected cards
          selectedCards.forEach(card => {
            if (card) {
              card.trainingEvents.forEach(event => {
                event.choices.forEach(choice => {
                  if (choice.skill) {
                    selectedSkillNames.add(choice.skill.name);
                  }
                });
              });
            }
          });
          
          // Filter skills to only show those from selected items
          skills = skills.filter(skill => selectedSkillNames.has(skill.name));
        }
        
        setFilteredSkills(skills);
        
        // Update suggestions based on search query and filter
        const suggestionResults = searchQuery.length >= 2 
          ? dataService.searchSkills(searchQuery).slice(0, 5)
          : dataService.getSkills().slice(0, 10); // Show first 10 when no search
        
        // Apply same filter to suggestions
        let filteredSuggestions = suggestionResults;
        if (hasSelectedItems && showOnlySelected) {
          const selectedSkillNames = new Set<string>();
          
          if (selectedCharacter) {
            selectedCharacter.events.forEach(event => {
              event.choices.forEach(choice => {
                if (choice.skill) {
                  selectedSkillNames.add(choice.skill.name);
                }
              });
            });
          }
          
          if (selectedScenario) {
            selectedScenario.events.forEach(event => {
              event.choices.forEach(choice => {
                if (choice.skill) {
                  selectedSkillNames.add(choice.skill.name);
                }
              });
            });
          }
          
          selectedCards.forEach(card => {
            if (card) {
              card.trainingEvents.forEach(event => {
                event.choices.forEach(choice => {
                  if (choice.skill) {
                    selectedSkillNames.add(choice.skill.name);
                  }
                });
              });
            }
          });
          
          filteredSuggestions = suggestionResults.filter(skill => selectedSkillNames.has(skill.name));
        }
        
        const suggestionData = filteredSuggestions.map((skill, index) => {
          // Get sources for this skill
          const sources = getSkillEventSources(skill.name);
          const sourceText = sources.length > 0 
            ? `Có thể nhận từ ${sources.length} nguồn`
            : 'Không có nguồn nào';
          
          return {
            id: `skill-${index}`,
            title: skill.name,
            subtitle: `${skill.effect.substring(0, 40)}${skill.effect.length > 40 ? '...' : ''} | ${sourceText}`,
            imageUrl: skill.imageUrl,
            source: 'skill',
            sourceName: 'Kỹ năng',
            data: skill
          };
        });
        setSuggestions(suggestionData);
      } catch (error) {
        console.error('Error loading skills:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadAndFilterSkills();
  }, [searchQuery, showOnlySelected, selectedCharacter, selectedScenario, selectedCards, hasSelectedItems, getSkillEventSources]);

  const handleSuggestionSelect = (suggestion: any) => {
    if (suggestion.data) {
      setSearchQuery(suggestion.data.name);
    }
  };

  const getSourceIcon = (source: string) => {
    switch (source) {
      case 'character': return '👤';
      case 'scenario': return '🎭';
      case 'card': return '🃏';
      default: return '📄';
    }
  };

  const getSourceColor = (source: string) => {
    switch (source) {
      case 'character': return 'bg-blue-100 text-blue-800';
      case 'scenario': return 'bg-purple-100 text-purple-800';
      case 'card': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">Tìm kiếm Kỹ năng</h2>
        
        <div className="flex items-center gap-4 mb-6">
          <div className="flex-1">
            <SearchInputWithDropdown
              value={searchQuery}
              onChange={setSearchQuery}
              onSuggestionSelect={handleSuggestionSelect}
              suggestions={suggestions}
              showSuggestions={showSuggestions}
              onShowSuggestionsChange={setShowSuggestions}
              placeholder="Tìm kiếm kỹ năng..."
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
              {showOnlySelected ? "Chỉ hiển thị kỹ năng đã chọn" : "Hiển thị tất cả kỹ năng"}
            </label>
          )}
        </div>

        {isLoading ? (
          <div className="text-center py-8">
            <p className="text-gray-500">Đang tải...</p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredSkills.map((skill) => {
              const eventSources = getSkillEventSources(skill.name);
              return (
                <div
                  key={skill.name}
                  className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-start gap-3 mb-3">
                    <img
                      src={skill.imageUrl}
                      alt={skill.name}
                      className="w-12 h-12 rounded object-cover flex-shrink-0"
                    />
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-800 mb-2">{skill.name}</h3>
                      <p className="text-sm text-gray-700 leading-relaxed">{skill.effect}</p>
                    </div>
                  </div>
                  
                  {/* Event Sources */}
                  {eventSources.length > 0 && (
                    <div className="mt-3">
                      <h4 className="text-sm font-medium text-gray-800 mb-2">Có thể nhận được từ:</h4>
                      <div className="space-y-2">
                        {eventSources.map((source, index) => (
                          <div key={index} className="bg-white p-2 rounded border text-sm">
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`px-2 py-1 rounded text-xs ${getSourceColor(source.source)}`}>
                                {getSourceIcon(source.source)} {source.sourceName}
                              </span>
                            </div>
                            <p className="text-gray-700 mb-1">
                              <span className="font-medium">Sự kiện:</span> {source.event}
                            </p>
                            <p className="text-gray-600">
                              <span className="font-medium">Lựa chọn:</span> {source.choice}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {searchQuery && filteredSkills.length === 0 && !isLoading && (
          <div className="text-center py-8">
            <p className="text-gray-500">Không tìm thấy kỹ năng nào cho "{searchQuery}"</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SkillsTab; 