import React, { useState, useRef, useEffect } from 'react';

interface ScrapeLog {
  id: string;
  timestamp: string;
  message: string;
  type: 'info' | 'success' | 'error' | 'warning';
}

const ScrapeTab: React.FC = () => {
  const [logs, setLogs] = useState<ScrapeLog[]>([]);
  const [runningScripts, setRunningScripts] = useState<Map<string, string>>(new Map()); // scriptName -> requestId
  const [lastClickTime, setLastClickTime] = useState<number>(0);
  const logsEndRef = useRef<HTMLDivElement>(null);
  
  // Prevent page reload when scripts complete
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (runningScripts.size > 0) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [runningScripts.size]);

  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  const addLog = (message: string, type: ScrapeLog['type'] = 'info') => {
    const newLog: ScrapeLog = {
      id: Date.now().toString(),
      timestamp: new Date().toLocaleTimeString(),
      message,
      type
    };
    setLogs(prev => [...prev, newLog]);
  };

  const runScrape = async (scriptName: string) => {
    // Debounce rapid clicks
    const now = Date.now();
    if (now - lastClickTime < 1000) { // 1 second debounce
      addLog('Vui lòng đợi 1 giây trước khi thử lại...', 'warning');
      return;
    }
    setLastClickTime(now);

    // Check if this specific script is already running
    if (runningScripts.has(scriptName)) {
      addLog(`${scriptName} đang chạy, vui lòng đợi...`, 'warning');
      return;
    }

    // Add script to running list
    setRunningScripts(prev => new Map(prev).set(scriptName, ''));
    
    // Remove duplicate log - server will send the initial message
    // addLog(`Bắt đầu chạy ${scriptName}...`, 'info');

    try {
      const response = await fetch('http://localhost:3001/api/scrape', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ script: scriptName }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Không thể đọc response stream');
      }

      const decoder = new TextDecoder();
      let requestId = '';
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;
        
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer
        
        for (const line of lines) {
          if (line.trim()) {
            try {
              const logData = JSON.parse(line);
              addLog(`[${scriptName}] ${logData.message}`, logData.type);
              
              // Set request ID from first message
              if (logData.requestId && !requestId) {
                const currentRequestId = logData.requestId;
                requestId = currentRequestId;
                setRunningScripts(prev => new Map(prev).set(scriptName, currentRequestId));
              }
            } catch {
              // Nếu không parse được JSON, coi như log thường
              addLog(`[${scriptName}] ${line}`, 'info');
            }
          }
        }
      }

      // Process any remaining buffer
      if (buffer.trim()) {
        try {
          const logData = JSON.parse(buffer);
          addLog(`[${scriptName}] ${logData.message}`, logData.type);
        } catch {
          addLog(`[${scriptName}] ${buffer}`, 'info');
        }
      }

      // Don't add success log here since the server will send it
    } catch (error) {
      addLog(`[${scriptName}] Lỗi khi chạy: ${error}`, 'error');
    } finally {
      setRunningScripts(prev => {
        const newMap = new Map(prev);
        newMap.delete(scriptName);
        return newMap;
      });
    }
  };

  const stopScrape = async (scriptName: string) => {
    const requestId = runningScripts.get(scriptName);
    if (!requestId) {
      addLog(`Không có script ${scriptName} nào đang chạy để dừng`, 'warning');
      return;
    }

    try {
      const response = await fetch('http://localhost:3001/api/stop-scrape', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ requestId: requestId }),
      });

      if (response.ok) {
        const result = await response.json();
        addLog(`[${scriptName}] ${result.message}`, 'success');
        setRunningScripts(prev => {
          const newMap = new Map(prev);
          newMap.delete(scriptName);
          return newMap;
        });
      } else {
        const error = await response.json();
        addLog(`[${scriptName}] Lỗi khi dừng script: ${error.error}`, 'error');
      }
    } catch (error) {
      addLog(`[${scriptName}] Lỗi khi dừng script: ${error}`, 'error');
    }
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const getLogTypeColor = (type: ScrapeLog['type']) => {
    switch (type) {
      case 'success': return 'text-green-600 bg-green-50';
      case 'error': return 'text-red-600 bg-red-50';
      case 'warning': return 'text-yellow-600 bg-yellow-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg shadow-md p-4">
        <h2 className="text-xl font-bold text-gray-800 mb-3">Chạy Scrape Dữ Liệu</h2>
        
        {/* Script Buttons */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          <button
            onClick={() => runScrape('uma-scrape.js')}
            disabled={runningScripts.has('uma-scrape.js')}
            className={`p-4 rounded-lg font-medium transition-all ${
              runningScripts.has('uma-scrape.js')
                ? 'bg-blue-100 text-blue-600 cursor-not-allowed'
                : 'bg-blue-500 text-white hover:bg-blue-600'
            }`}
          >
            {runningScripts.has('uma-scrape.js') ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Đang chạy...</span>
              </div>
            ) : (
              'Chạy Uma Scrape'
            )}
          </button>

          <button
            onClick={() => runScrape('support-scrape.js')}
            disabled={runningScripts.has('support-scrape.js')}
            className={`p-4 rounded-lg font-medium transition-all ${
              runningScripts.has('support-scrape.js')
                ? 'bg-green-100 text-green-600 cursor-not-allowed'
                : 'bg-green-500 text-white hover:bg-green-600'
            }`}
          >
            {runningScripts.has('support-scrape.js') ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Đang chạy...</span>
              </div>
            ) : (
              'Chạy Support Scrape'
            )}
          </button>

          <button
            onClick={() => runScrape('skill-scrape.js')}
            disabled={runningScripts.has('skill-scrape.js')}
            className={`p-4 rounded-lg font-medium transition-all ${
              runningScripts.has('skill-scrape.js')
                ? 'bg-purple-100 text-purple-600 cursor-not-allowed'
                : 'bg-purple-500 text-white hover:bg-purple-600'
            }`}
          >
            {runningScripts.has('skill-scrape.js') ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Đang chạy...</span>
              </div>
            ) : (
              'Chạy Skill Scrape'
            )}
          </button>

          <button
            onClick={() => runScrape('scenario-scrape.js')}
            disabled={runningScripts.has('scenario-scrape.js')}
            className={`p-4 rounded-lg font-medium transition-all ${
              runningScripts.has('scenario-scrape.js')
                ? 'bg-orange-100 text-orange-600 cursor-not-allowed'
                : 'bg-orange-500 text-white hover:bg-orange-600'
            }`}
          >
            {runningScripts.has('scenario-scrape.js') ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Đang chạy...</span>
              </div>
            ) : (
              'Chạy Scenario Scrape'
            )}
          </button>
        </div>

        {/* Log Controls */}
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-base font-semibold text-gray-800">Log Output</h3>
          <div className="flex space-x-2">
            {runningScripts.size > 0 && (
              <div className="flex space-x-2">
                {Array.from(runningScripts.keys()).map(scriptName => (
                  <button
                    key={scriptName}
                    onClick={() => stopScrape(scriptName)}
                    className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                  >
                    ⏹️ Dừng {scriptName}
                  </button>
                ))}
              </div>
            )}
            <button
              onClick={clearLogs}
              className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
            >
              Xóa Log
            </button>
          </div>
        </div>

        {/* Log Display */}
        <div className="bg-gray-900 text-green-400 rounded-lg p-3 h-80 overflow-y-auto font-mono text-sm">
          {logs.length === 0 ? (
            <div className="text-gray-500 text-center py-8">
              Chưa có log nào. Hãy chạy một script để xem log.
            </div>
          ) : (
            logs.map((log) => (
              <div key={log.id} className="mb-2">
                <span className="text-gray-500">[{log.timestamp}]</span>
                <span className={`ml-2 px-2 py-1 rounded text-xs ${getLogTypeColor(log.type)}`}>
                  {log.type.toUpperCase()}
                </span>
                <span className="ml-2">{log.message}</span>
              </div>
            ))
          )}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
};

export default ScrapeTab; 