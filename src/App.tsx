import React, { useState, useEffect } from 'react';
import { UmaCharacter, Scenario, SupportCard } from './types';
import SelectionGrid from './components/SelectionGrid';
import EventDisplay from './components/EventDisplay';
import SkillsTab from './components/SkillsTab';
import ScrapeTab from './components/ScrapeTab';
import EventScannerTab from './components/EventScannerTab';

type TabType = 'selection' | 'events' | 'skills' | 'scrape' | 'scanner';

// Local storage keys
const STORAGE_KEYS = {
  SELECTED_CHARACTER: 'uma_selected_character',
  SELECTED_SCENARIO: 'uma_selected_scenario',
  SELECTED_CARDS: 'uma_selected_cards',
  ACTIVE_TAB: 'uma_active_tab'
};

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('selection');
  const [selectedCharacter, setSelectedCharacter] = useState<UmaCharacter | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(null);
  const [selectedCards, setSelectedCards] = useState<(SupportCard | null)[]>(Array(6).fill(null));

  // Load saved state from localStorage on component mount
  useEffect(() => {
    try {
      // Load active tab
      const savedTab = localStorage.getItem(STORAGE_KEYS.ACTIVE_TAB) as TabType;
      if (savedTab && ['selection', 'events', 'skills', 'scrape', 'scanner'].includes(savedTab)) {
        setActiveTab(savedTab);
      }

      // Load selected character
      const savedCharacter = localStorage.getItem(STORAGE_KEYS.SELECTED_CHARACTER);
      if (savedCharacter) {
        setSelectedCharacter(JSON.parse(savedCharacter));
      }

      // Load selected scenario
      const savedScenario = localStorage.getItem(STORAGE_KEYS.SELECTED_SCENARIO);
      if (savedScenario) {
        setSelectedScenario(JSON.parse(savedScenario));
      }

      // Load selected cards
      const savedCards = localStorage.getItem(STORAGE_KEYS.SELECTED_CARDS);
      if (savedCards) {
        try {
          const parsedCards = JSON.parse(savedCards);
          // Ensure we always have exactly 6 elements
          if (Array.isArray(parsedCards)) {
            const normalizedCards = Array(6).fill(null);
            parsedCards.forEach((card, index) => {
              if (index < 6 && card !== null) {
                normalizedCards[index] = card;
              }
            });
            setSelectedCards(normalizedCards);
            console.log('Loaded cards from localStorage:', normalizedCards.filter(c => c !== null).map(c => c?.name));
          } else {
            setSelectedCards(Array(6).fill(null));
          }
        } catch (parseError) {
          console.error('Error parsing saved cards:', parseError);
          setSelectedCards(Array(6).fill(null));
        }
      }
    } catch (error) {
      console.error('Error loading saved state:', error);
    }
  }, []);

  // Save state to localStorage whenever selections change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEYS.ACTIVE_TAB, activeTab);
    } catch (error) {
      console.error('Error saving active tab:', error);
    }
  }, [activeTab]);

  useEffect(() => {
    try {
      if (selectedCharacter) {
        localStorage.setItem(STORAGE_KEYS.SELECTED_CHARACTER, JSON.stringify(selectedCharacter));
      } else {
        localStorage.removeItem(STORAGE_KEYS.SELECTED_CHARACTER);
      }
    } catch (error) {
      console.error('Error saving selected character:', error);
    }
  }, [selectedCharacter]);

  useEffect(() => {
    try {
      if (selectedScenario) {
        localStorage.setItem(STORAGE_KEYS.SELECTED_SCENARIO, JSON.stringify(selectedScenario));
      } else {
        localStorage.removeItem(STORAGE_KEYS.SELECTED_SCENARIO);
      }
    } catch (error) {
      console.error('Error saving selected scenario:', error);
    }
  }, [selectedScenario]);

  useEffect(() => {
    try {
      // Only save if there are actual cards selected (not all null)
      const hasCards = selectedCards.some(card => card !== null);
      if (hasCards) {
        localStorage.setItem(STORAGE_KEYS.SELECTED_CARDS, JSON.stringify(selectedCards));
        console.log('Saved cards to localStorage:', selectedCards.filter(c => c !== null).map(c => c?.name));
      } else {
        localStorage.removeItem(STORAGE_KEYS.SELECTED_CARDS);
        console.log('Removed cards from localStorage (no cards selected)');
      }
    } catch (error) {
      console.error('Error saving selected cards:', error);
    }
  }, [selectedCards]);

  const handleCardSelect = (card: SupportCard | null, index: number) => {
    const newCards = [...selectedCards];
    newCards[index] = card;
    setSelectedCards(newCards);
    console.log('Card selected:', { card: card?.name, index, totalCards: newCards.filter(c => c !== null).length });
  };

  const clearAllSelections = () => {
    setSelectedCharacter(null);
    setSelectedScenario(null);
    setSelectedCards(Array(6).fill(null));
    setActiveTab('selection');
    
    // Clear localStorage
    try {
      localStorage.removeItem(STORAGE_KEYS.SELECTED_CHARACTER);
      localStorage.removeItem(STORAGE_KEYS.SELECTED_SCENARIO);
      localStorage.removeItem(STORAGE_KEYS.SELECTED_CARDS);
      localStorage.removeItem(STORAGE_KEYS.ACTIVE_TAB);
    } catch (error) {
      console.error('Error clearing localStorage:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-4">
        <header className="text-center mb-4">
          <h1 className="text-2xl font-bold text-gray-800 mb-1">Uma Project Data Viewer</h1>
          <p className="text-sm text-gray-600">Chọn nhân vật, kịch bản và thẻ hỗ trợ để xem các sự kiện liên quan</p>
        </header>

        {/* Tab Navigation */}
        <div className="flex justify-center mb-4">
          <div className="bg-white rounded-lg shadow-md p-1">
            <div className="flex space-x-1">
              <button
                onClick={() => setActiveTab('selection')}
                className={`px-6 py-2 rounded-md font-medium transition-colors ${
                  activeTab === 'selection'
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                Chọn Lựa
              </button>
              <button
                onClick={() => setActiveTab('events')}
                className={`px-6 py-2 rounded-md font-medium transition-colors ${
                  activeTab === 'events'
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                Sự Kiện
              </button>
              <button
                onClick={() => setActiveTab('skills')}
                className={`px-6 py-2 rounded-md font-medium transition-colors ${
                  activeTab === 'skills'
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                Kỹ Năng
              </button>
              <button
                onClick={() => setActiveTab('scrape')}
                className={`px-6 py-2 rounded-md font-medium transition-colors ${
                  activeTab === 'scrape'
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                Scrape Data
              </button>
              <button
                onClick={() => setActiveTab('scanner')}
                className={`px-6 py-2 rounded-md font-medium transition-colors ${
                  activeTab === 'scanner'
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                Quét Event
              </button>
            </div>
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === 'selection' && (
          <SelectionGrid
            selectedCharacter={selectedCharacter}
            selectedScenario={selectedScenario}
            selectedCards={selectedCards}
            onCharacterSelect={setSelectedCharacter}
            onScenarioSelect={setSelectedScenario}
            onCardSelect={handleCardSelect}
            onClearAllSelections={clearAllSelections}
          />
        )}

        {activeTab === 'events' && (
          <EventDisplay
            character={selectedCharacter}
            scenario={selectedScenario}
            cards={selectedCards.filter(card => card !== null) as SupportCard[]}
          />
        )}

        {activeTab === 'skills' && (
          <SkillsTab
            selectedCharacter={selectedCharacter}
            selectedScenario={selectedScenario}
            selectedCards={selectedCards}
          />
        )}

        {activeTab === 'scrape' && <ScrapeTab />}

        {activeTab === 'scanner' && (
          <EventScannerTab
            selectedCharacter={selectedCharacter}
            selectedScenario={selectedScenario}
            selectedCards={selectedCards}
          />
        )}
      </div>
    </div>
  );
};

export default App; 