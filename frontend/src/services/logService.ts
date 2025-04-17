import { LogEntry, LogLevel } from '../types/logEntry';

// TODO: Replace with actual API base URL, potentially from env vars
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// Function to get the auth token (reuse or centralize this logic later)
const getAuthToken = (): string | null => {
  return localStorage.getItem('authToken');
};

// Helper function for making authenticated API requests (reuse or centralize)
const fetchWithAuth = async (url: string, options: RequestInit = {}): Promise<Response> => {
  const token = getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
  };

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: 'Failed to parse error response' }));
    console.error('API Error:', response.status, errorData);
    throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
  }
  return response;
};

// --- API Functions ---

// Fetch latest log entries (limit and level filtering might be query params)
export const getLogs = async (limit: number = 200, level?: LogLevel): Promise<LogEntry[]> => {
  try {
    let url = `${API_BASE_URL}/logs?limit=${limit}`;
    if (level) {
      url += `&level=${level}`;
    }
    const response = await fetchWithAuth(url);
    const data: LogEntry[] = await response.json();
    // TODO: Add data validation/transformation if necessary (e.g., parse timestamp)
    return data.map(log => ({
        ...log,
        // Ensure timestamp is handled correctly if needed (e.g., new Date(log.timestamp))
    }));
  } catch (error) {
    console.error('Failed to fetch logs:', error);
    throw error;
  }
};