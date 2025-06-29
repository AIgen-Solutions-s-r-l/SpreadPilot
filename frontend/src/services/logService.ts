import apiClient from './api';
import { 
  LogsResponseSchema,
  type LogEntry,
  type LogLevel,
  type LogsResponse
} from '../schemas/log.schema';

// Fetch recent logs with optional filtering
export const getLogs = async (
  limit: number = 200, 
  level?: LogLevel,
  service?: string,
  search?: string
): Promise<LogsResponse> => {
  try {
    // Build query parameters
    const params: any = { n: limit };
    if (level) params.level = level;
    if (service) params.service = service;
    if (search) params.search = search;
    
    const response = await apiClient.get('/logs/recent', { params });
    
    // Validate response data with Zod
    const validatedData = LogsResponseSchema.parse(response.data);
    return validatedData;
  } catch (error) {
    console.error('Failed to fetch logs:', error);
    if (error && typeof error === 'object' && 'issues' in error) {
      // Zod validation error
      console.error('Validation errors:', (error as any).issues);
    }
    throw error;
  }
};

// Get logs as array (for backward compatibility)
export const getLogsArray = async (
  limit: number = 200,
  level?: LogLevel,
  service?: string,
  search?: string
): Promise<LogEntry[]> => {
  const response = await getLogs(limit, level, service, search);
  return response.logs;
};

// Stream logs via WebSocket (if needed)
export const streamLogs = (onMessage: (log: LogEntry) => void): (() => void) => {
  const wsUrl = import.meta.env.VITE_API_BASE_URL?.replace('http', 'ws') || 'ws://localhost:8083';
  const ws = new WebSocket(`${wsUrl}/api/v1/ws/logs`);
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      // Validate individual log entry
      const validatedLog = LogsResponseSchema.shape.logs.element.parse(data);
      onMessage(validatedLog);
    } catch (error) {
      console.error('Failed to parse WebSocket log message:', error);
    }
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };
  
  // Return cleanup function
  return () => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
  };
};