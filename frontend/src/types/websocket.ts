export interface WebSocketMessage {
  type: string;
  data: unknown;
  timestamp?: string;
}

export interface LogEntryMessage extends WebSocketMessage {
  type: 'log_entry';
  data: {
    level: string;
    message: string;
    service: string;
    timestamp: string;
    details?: Record<string, unknown>;
  };
}