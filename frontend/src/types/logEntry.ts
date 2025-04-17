export enum LogLevel {
  INFO = 'INFO',
  WARNING = 'WARNING',
  ERROR = 'ERROR',
  DEBUG = 'DEBUG', // Include DEBUG if backend provides it
  // Add other levels if necessary
}

export interface LogEntry {
  id: string; // Or number, depending on backend
  timestamp: string; // ISO string format ideally
  level: LogLevel;
  message: string;
  // Add any other relevant fields from the backend log structure
  // e.g., serviceName?: string;
  // e.g., followerId?: string;
}