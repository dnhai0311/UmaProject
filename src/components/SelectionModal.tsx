import React, { useState, useEffect, useRef } from 'react';
import { UmaCharacter, Scenario, SupportCard } from '../types';
import { dataService } from '../services/dataService';
import SearchInput from './SearchInput';

interface SelectionModalProps {
  type: 'character' | 'scenario' | 'card';
  onClose: () => void;
  onCharacterSelect: (character: UmaCharacter) => void;
  onScenarioSelect: (scenario: Scenario) => void;
  onCardSelect: (card: SupportCard | null, cardToRemove?: SupportCard) => void;
  selectedCards?: SupportCard[];
}

const SelectionModal: React.FC<SelectionModalProps> = ({
  type,
  onClose,
  onCharacterSelect,
  onScenarioSelect,
  onCardSelect,
  selectedCards = []
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [rarityFilter, setRarityFilter] = useState('');
  const [filteredItems, setFilteredItems] = useState<any[]>([]);
  const [rarities, setRarities] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoading(true);
        await dataService.loadAllData();
        
        switch (type) {
          case 'character':
            const characters = dataService.getUmaCharacters();
            setFilteredItems(characters);
            break;
          case 'scenario':
            const scenarios = dataService.getScenarios();
            setFilteredItems(scenarios);
            break;
          case 'card':
            const cards = dataService.getSupportCards();
            const allRarities = dataService.getRarities();
            setFilteredItems(cards);
            setRarities(allRarities);
            break;
        }
      } catch (error) {
        console.error('Error loading data:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadData();
  }, [type]);

  useEffect(() => {
    let filtered: any[] = [];
    
    switch (type) {
      case 'character':
        filtered = dataService.searchUmaCharacters(searchQuery);
        break;
      case 'scenario':
        filtered = dataService.searchScenarios(searchQuery);
        break;
      case 'card':
        filtered = dataService.searchSupportCards(searchQuery, rarityFilter);
        break;
    }
    
    setFilteredItems(filtered);
  }, [searchQuery, rarityFilter, type]);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [onClose]);

  const getTitle = () => {
    switch (type) {
      case 'character': return 'Chọn Nhân Vật';
      case 'scenario': return 'Chọn Kịch Bản';
      case 'card': return 'Chọn Thẻ Hỗ Trợ';
    }
  };

  const getPlaceholder = () => {
    switch (type) {
      case 'character': return 'Tìm kiếm nhân vật...';
      case 'scenario': return 'Tìm kiếm kịch bản...';
      case 'card': return 'Tìm kiếm thẻ...';
    }
  };

  const handleItemSelect = (item: any) => {
    switch (type) {
      case 'character':
        onCharacterSelect(item);
        onClose(); // Close modal for character and scenario
        break;
      case 'scenario':
        onScenarioSelect(item);
        onClose(); // Close modal for character and scenario
        break;
      case 'card':
        // Check if this card is already selected
        const isSelected = isCardSelected(item);
        if (isSelected) {
          // Xóa thẻ này
          onCardSelect(null, item);
        } else {
          // Thêm thẻ mới
          onCardSelect(item);
        }
        // Không đóng modal
        break;
    }
  };

  const isCardSelected = (card: SupportCard) => {
    return selectedCards.some(selected => 
      selected.name === card.name && selected.url_detail === card.url_detail
    );
  };

  const getCardSlotNumber = (card: SupportCard) => {
    const index = selectedCards.findIndex(selected => 
      selected.name === card.name && selected.url_detail === card.url_detail
    );
    return index !== -1 ? index + 1 : null;
  };

  const renderItem = (item: any, index: number) => {
    switch (type) {
      case 'character':
        return (
          <div
            key={item.name}
            onClick={() => handleItemSelect(item)}
            className="p-3 border border-gray-200 rounded-lg cursor-pointer hover:shadow-md transition-all"
          >
            <div className="flex items-center space-x-3">
              <img
                src={item.imageUrl}
                alt={item.name}
                className="w-12 h-12 rounded-lg object-cover flex-shrink-0"
                onError={(e) => {
                  e.currentTarget.src = 'https://via.placeholder.com/48x48?text=No+Image';
                }}
              />
              <div className="flex-1 min-w-0">
                <h3 className="font-medium text-gray-800 truncate">{item.name}</h3>
                <p className="text-sm text-gray-600">{item.rarity}</p>
              </div>
            </div>
          </div>
        );
      
      case 'scenario':
        return (
          <div
            key={item.name}
            onClick={() => handleItemSelect(item)}
            className="p-3 border border-gray-200 rounded-lg cursor-pointer hover:shadow-md transition-all"
          >
            <div className="flex items-center space-x-3">
              {item.imageUrl ? (
                <img
                  src={item.imageUrl}
                  alt={item.name}
                  className="w-12 h-12 rounded-lg object-cover flex-shrink-0"
                  onError={(e) => {
                    e.currentTarget.src = 'https://via.placeholder.com/48x48?text=No+Image';
                  }}
                />
              ) : (
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <svg className="w-6 h-6 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
              <div className="flex-1 min-w-0">
                <h3 className="font-medium text-gray-800">{item.name}</h3>
                <p className="text-sm text-gray-600">{item.events.length} sự kiện</p>
              </div>
            </div>
          </div>
        );
      
      case 'card':
        const isSelected = isCardSelected(item);
        const slotNumber = getCardSlotNumber(item);
        
        return (
          <div
            key={item.name}
            onClick={() => handleItemSelect(item)}
            className={`p-3 border rounded-lg cursor-pointer transition-all ${
              isSelected 
                ? 'border-purple-500 bg-purple-50' 
                : 'border-gray-200 hover:shadow-md'
            }`}
          >
            <div className="flex items-center space-x-3">
              <img
                src={item.imageUrl}
                alt={item.name}
                className="w-12 h-12 rounded-lg object-cover flex-shrink-0"
                onError={(e) => {
                  e.currentTarget.src = 'https://via.placeholder.com/48x48?text=No+Image';
                }}
              />
              <div className="flex-1 min-w-0">
                <h3 className="font-medium text-gray-800 truncate">{item.name}</h3>
                <p className="text-sm text-gray-600">{item.rarity}</p>
                <p className="text-xs text-gray-500">{item.trainingEvents.length} sự kiện</p>
              </div>
              {isSelected && (
                <div className="flex items-center space-x-2">
                  <div className="bg-purple-500 text-white text-xs px-2 py-1 rounded-full">
                    Ô {slotNumber}
                  </div>
                  <div className="text-purple-500">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>
              )}
            </div>
          </div>
        );
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div ref={modalRef} className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-800">{getTitle()}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Search and Filters */}
        <div className="p-6 border-b border-gray-200">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SearchInput
              value={searchQuery}
              onChange={setSearchQuery}
              placeholder={getPlaceholder()}
            />
            
            {type === 'card' && (
              <select
                value={rarityFilter}
                onChange={(e) => setRarityFilter(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Tất cả độ hiếm</option>
                {rarities.map((rarity) => (
                  <option key={rarity} value={rarity}>
                    {rarity}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="text-center py-8">
              <p className="text-gray-600">Đang tải...</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredItems.map(renderItem)}
            </div>
          )}

          {filteredItems.length === 0 && !isLoading && (
            <div className="text-center py-8">
              <p className="text-gray-600">Không tìm thấy kết quả nào.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SelectionModal; 