import React, { useState } from 'react';
import { UmaCharacter, Scenario, SupportCard } from '../types';

interface EventScannerTabProps {
  selectedCharacter: UmaCharacter | null;
  selectedScenario: Scenario | null;
  selectedCards: (SupportCard | null)[];
}

const EventScannerTab: React.FC<EventScannerTabProps> = ({
  selectedCharacter,
  selectedScenario,
  selectedCards
}) => {
  const [isScanning, setIsScanning] = useState(false);

  const startEventScanner = async () => {
    setIsScanning(true);
    
    // Chuẩn bị dữ liệu để gửi cho Python script
    const scanData = {
      character: selectedCharacter,
      scenario: selectedScenario,
      cards: selectedCards.filter(card => card !== null),
      timestamp: new Date().toISOString()
    };

    try {
      // Gọi API để khởi động Python scanner
      const response = await fetch('/api/start-event-scanner', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(scanData)
      });

      if (response.ok) {
        console.log('Event scanner started successfully');
        // Có thể thêm logic để nhận kết quả real-time qua WebSocket
      } else {
        console.error('Failed to start event scanner');
      }
    } catch (error) {
      console.error('Error starting event scanner:', error);
    } finally {
      setIsScanning(false);
    }
  };

  const stopEventScanner = async () => {
    try {
      const response = await fetch('/api/stop-event-scanner', {
        method: 'POST'
      });

      if (response.ok) {
        console.log('Event scanner stopped successfully');
        setIsScanning(false);
      }
    } catch (error) {
      console.error('Error stopping event scanner:', error);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-800 mb-2">Quét Event</h2>
        <p className="text-gray-600">
          Sử dụng AI để quét và nhận diện các event trong game thông qua hình ảnh
        </p>
      </div>

      {/* Hiển thị thông tin đã chọn */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <h3 className="font-semibold text-gray-700 mb-3">Thông tin đã chọn:</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <span className="text-sm text-gray-500">Nhân vật:</span>
            <p className="font-medium">{selectedCharacter?.name || 'Chưa chọn'}</p>
          </div>
          <div>
            <span className="text-sm text-gray-500">Kịch bản:</span>
            <p className="font-medium">{selectedScenario?.name || 'Chưa chọn'}</p>
          </div>
          <div>
            <span className="text-sm text-gray-500">Thẻ hỗ trợ:</span>
            <p className="font-medium">
              {selectedCards.filter(card => card !== null).length}/6 thẻ
            </p>
          </div>
        </div>
      </div>

      {/* Nút điều khiển scanner */}
      <div className="mb-6">
        <div className="flex gap-4">
          <button
            onClick={startEventScanner}
            disabled={isScanning}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              isScanning
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-green-500 text-white hover:bg-green-600'
            }`}
          >
            {isScanning ? 'Đang quét...' : 'Bắt đầu quét Event'}
          </button>
          
          {isScanning && (
            <button
              onClick={stopEventScanner}
              className="px-6 py-3 rounded-lg font-medium bg-red-500 text-white hover:bg-red-600 transition-colors"
            >
              Dừng quét
            </button>
          )}
        </div>
      </div>

      {/* Hướng dẫn sử dụng */}
      <div className="mb-6 p-4 bg-blue-50 rounded-lg">
        <h3 className="font-semibold text-blue-800 mb-2">Hướng dẫn sử dụng:</h3>
        <ol className="list-decimal list-inside text-blue-700 space-y-1">
          <li>Chọn nhân vật, kịch bản và thẻ hỗ trợ ở tab "Chọn Lựa"</li>
          <li>Nhấn "Bắt đầu quét Event" để khởi động trình quét</li>
          <li>Chọn vùng màn hình cần quét event</li>
          <li>Trình quét sẽ tự động nhận diện và hiển thị thông tin event</li>
        </ol>
      </div>

      {/* Trạng thái scanner */}
      {isScanning && (
        <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex items-center">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-yellow-600 mr-2"></div>
            <span className="text-yellow-800">Đang quét event...</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default EventScannerTab; 