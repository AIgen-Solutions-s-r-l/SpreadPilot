import React, { useState, useEffect, useCallback } from 'react';
import type { LogEntry } from '../schemas/log.schema';
import { LogLevel } from '../schemas/log.schema';
import * as logService from '../services/logService';
import { useWebSocket } from '../hooks/useWebSocket'; // Import WebSocket hook

const LogsPage: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [filterLevel, setFilterLevel] = useState<LogLevel | ''>(''); // State for level filter

  const { lastMessage, isConnected } = useWebSocket(); // Get WebSocket state

  const fetchLogs = useCallback(async (level: LogLevel | '' = filterLevel) => {
    setIsLoading(true);
    setError(null);
    try {
      // Pass undefined if filterLevel is empty string
      const data = await logService.getLogs(200, level || undefined);
      setLogs(data.logs || []);
    } catch (err) {
      setError('Failed to fetch logs.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [filterLevel]); // Depend on filterLevel

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]); // Fetch logs on initial load and when fetchLogs changes (due to filterLevel)

  // --- WebSocket Update Handling ---
  useEffect(() => {
    if (lastMessage) {
      // TODO: Implement more specific logic based on message content
      console.log('Processing WebSocket message in LogsPage:', lastMessage);
      if (lastMessage.type === 'log_entry') {
        const newLog = lastMessage.data as LogEntry;
        // Add new log to the top, respecting the filter and limit (optional)
        setLogs(prevLogs => {
          // Check if the new log matches the current filter
          if (!filterLevel || newLog.level === filterLevel) {
            // Add new log and potentially trim the list to maintain the limit (e.g., 200)
            const updatedLogs = [newLog, ...prevLogs];
            // return updatedLogs.slice(0, 200); // Optional: Keep list size limited
            return updatedLogs;
          }
          return prevLogs; // No change if filter doesn't match
        });
      }
      // Add more specific update logic based on message structure from backend
    }
  }, [lastMessage, filterLevel]); // Re-evaluate when message or filter changes

  const handleFilterChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const newLevel = event.target.value as LogLevel | '';
    setFilterLevel(newLevel);
    // Fetch logs with the new filter immediately
    // fetchLogs(newLevel); // fetchLogs dependency array handles this
  };

  // Helper to get color based on log level
  const getLevelColor = (level: LogLevel): string => {
    switch (level) {
      case LogLevel.ERROR: return 'text-red-600';
      case LogLevel.WARNING: return 'text-yellow-600';
      case LogLevel.INFO: return 'text-blue-600';
      case LogLevel.DEBUG: return 'text-gray-500';
      default: return 'text-gray-700';
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-semibold text-gray-800">Log Console</h1>
        <div className="flex items-center space-x-4">
           {/* TODO: Add WebSocket connection status indicator */}
           <span className={`text-sm ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
             WebSocket: {isConnected ? 'Connected' : 'Disconnected'}
           </span>
           <div>
             <label htmlFor="levelFilter" className="mr-2 text-sm font-medium text-gray-700">Filter by Level:</label>
             <select
               id="levelFilter"
               value={filterLevel}
               onChange={handleFilterChange}
               className="p-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
             >
               <option value="">All</option>
               {Object.values(LogLevel).map(level => (
                 <option key={level} value={level}>{level}</option>
               ))}
             </select>
           </div>
        </div>
      </div>

      {isLoading && <div className="text-center p-4">Loading logs...</div>}
      {error && <div className="p-4 text-red-600 bg-red-100 rounded">{error}</div>}

      {!isLoading && !error && (
        <div className="bg-white rounded shadow overflow-hidden">
          {/* Consider virtualization for very large log lists */}
          <div className="h-[70vh] overflow-y-auto p-4 font-mono text-sm space-y-1">
            {logs.length === 0 ? (
              <p className="text-gray-500">No log entries found.</p>
            ) : (
              logs.map((log) => (
                <div key={log.id} className="whitespace-pre-wrap break-words">
                  <span className="text-gray-400 mr-2">
                    {/* Format timestamp nicely */}
                    {new Date(log.timestamp).toLocaleString()}
                  </span>
                  <span className={`font-semibold ${getLevelColor(log.level)} mr-2`}>
                    [{log.level}]
                  </span>
                  <span>{log.message}</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default LogsPage;