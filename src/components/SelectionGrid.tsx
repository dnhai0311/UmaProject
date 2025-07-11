import React, { useState } from 'react';
import { UmaCharacter, Scenario, SupportCard } from '../types';
import SelectionModal from './SelectionModal';

interface SelectionGridProps {
  selectedCharacter: UmaCharacter | null;
  selectedScenario: Scenario | null;
  selectedCards: (SupportCard | null)[];
  onCharacterSelect: (character: UmaCharacter | null) => void;
  onScenarioSelect: (scenario: Scenario | null) => void;
  onCardSelect: (card: SupportCard | null, index: number) => void;
  onClearAllSelections: () => void;
}

const SelectionGrid: React.FC<SelectionGridProps> = ({
  selectedCharacter,
  selectedScenario,
  selectedCards,
  onCharacterSelect,
  onScenarioSelect,
  onCardSelect,
  onClearAllSelections,
}) => {
  const [modalType, setModalType] = useState<'character' | 'scenario' | 'card' | null>(null);

  const handleCardClick = (index: number) => {
    setModalType('card');
  };

  const handleCardRemove = (index: number) => {
    onCardSelect(null, index);
  };

  const handleCardSelect = (card: SupportCard | null, cardToRemove?: SupportCard) => {
    if (card === null && cardToRemove) {
      // Xóa thẻ cụ thể - tìm index của thẻ cần xóa
      const indexToRemove = selectedCards.findIndex(c => 
        c && c.name === cardToRemove.name && c.url_detail === cardToRemove.url_detail
      );
      if (indexToRemove !== -1) {
        onCardSelect(null, indexToRemove);
      }
    } else if (card) {
      // Thêm thẻ mới vào ô trống đầu tiên
      const emptyIndex = selectedCards.findIndex(c => c === null);
      if (emptyIndex !== -1) {
        onCardSelect(card, emptyIndex);
      }
    }
  };

  const handleCloseModal = () => {
    setModalType(null);
  };

  return (
    <div className="space-y-6">
      {/* Character and Scenario Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Character Selector */}
        <div
          onClick={() => setModalType('character')}
          className="p-4 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-all min-h-[140px] flex items-center"
        >
          {selectedCharacter ? (
            <div className="flex items-center space-x-4 w-full">
              <img
                src={selectedCharacter.imageUrl}
                alt={selectedCharacter.name}
                className="w-16 h-16 rounded-lg object-cover flex-shrink-0"
                onError={(e) => {
                  e.currentTarget.src = 'https://via.placeholder.com/64x64?text=No+Image';
                }}
              />
              <div className="flex-1">
                <h3 className="font-semibold text-gray-800 text-lg">{selectedCharacter.name}</h3>
                <p className="text-gray-600">{selectedCharacter.rarity}</p>
              </div>
            </div>
          ) : (
            <div className="text-center text-gray-500 w-full">
              <svg className="w-12 h-12 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <p className="text-lg font-medium">Chọn Nhân Vật</p>
            </div>
          )}
        </div>

        {/* Scenario Selector */}
        <div
          onClick={() => setModalType('scenario')}
          className="p-4 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer hover:border-green-400 hover:bg-green-50 transition-all min-h-[140px] flex items-center"
        >
          {selectedScenario ? (
            <div className="flex items-center space-x-4 w-full">
              {selectedScenario.imageUrl ? (
                <img
                  src={selectedScenario.imageUrl}
                  alt={selectedScenario.name}
                  className="w-16 h-16 rounded-lg object-cover flex-shrink-0"
                  onError={(e) => {
                    e.currentTarget.src = 'https://via.placeholder.com/64x64?text=No+Image';
                  }}
                />
              ) : (
                <div className="w-16 h-16 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <svg className="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
              <div className="flex-1">
                <h3 className="font-semibold text-gray-800 text-lg">{selectedScenario.name}</h3>
                <p className="text-gray-600">{selectedScenario.events.length} sự kiện</p>
              </div>
            </div>
          ) : (
            <div className="text-center text-gray-500 w-full">
              <svg className="w-12 h-12 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-lg font-medium">Chọn Kịch Bản</p>
            </div>
          )}
        </div>
      </div>

      {/* Support Cards Grid */}
      <div>
        <h3 className="text-lg font-semibold text-gray-800 mb-3">Thẻ Hỗ Trợ</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {selectedCards.map((card, index) => (
            <div
              key={index}
              onClick={() => handleCardClick(index)}
              className={`p-3 border-2 rounded-xl cursor-pointer transition-all min-h-[200px] flex flex-col relative ${
                card
                  ? 'border-purple-300 bg-purple-50 hover:border-red-400 hover:bg-red-50'
                  : 'border-dashed border-gray-300 hover:border-purple-400 hover:bg-purple-50'
              }`}
            >
              {card ? (
                <>
                  {/* Nút xóa */}
                  <button
                    className="absolute top-2 right-2 w-7 h-7 flex items-center justify-center bg-red-500 text-white rounded-full shadow hover:bg-red-600 z-10"
                    onClick={e => {
                      e.stopPropagation();
                      handleCardRemove(index);
                    }}
                    title="Xóa thẻ này"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                  <div className="text-center flex-1 flex flex-col justify-center">
                    <img
                      src={card.imageUrl}
                      alt={card.name}
                      className="w-14 h-14 rounded-lg object-cover mx-auto mb-3"
                      onError={(e) => {
                        e.currentTarget.src = 'https://via.placeholder.com/56x56?text=No+Image';
                      }}
                    />
                    <p className="text-sm font-medium text-gray-800 truncate mb-1">{card.name}</p>
                    <p className="text-xs text-gray-600 mb-2">{card.rarity}</p>
                  </div>
                </>
              ) : (
                <div className="text-center text-gray-500 flex-1 flex flex-col justify-center">
                  <svg className="w-10 h-10 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  <p className="text-sm font-medium">Ô {index + 1}</p>
                </div>
              )}
            </div>
          ))}
        </div>
        
        {/* Clear All Button */}
        {(selectedCharacter || selectedScenario || selectedCards.some(card => card !== null)) && (
          <button
            onClick={onClearAllSelections}
            className="mt-4 w-full px-6 py-3 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors font-medium text-lg"
          >
            Xóa Tất Cả Lựa Chọn
          </button>
        )}
      </div>

      {/* Modal */}
      {modalType && (
        <SelectionModal
          type={modalType}
          onClose={handleCloseModal}
          onCharacterSelect={onCharacterSelect}
          onScenarioSelect={onScenarioSelect}
          onCardSelect={handleCardSelect}
          selectedCards={selectedCards.filter(card => card !== null) as SupportCard[]}
        />
      )}
    </div>
  );
};

export default SelectionGrid; 