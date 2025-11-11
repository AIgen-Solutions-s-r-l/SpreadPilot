// Message handler type for subscriptions
export type MessageHandler = (data: any) => void;

// Base WebSocket message structure
export interface WebSocketMessage {
  type: string;
  data: unknown;
  timestamp?: string;
}

// Message type constants
export const WebSocketMessageType = {
  FOLLOWER_UPDATE: 'follower_update',
  LOG_ENTRY: 'log_entry',
  POSITION_UPDATE: 'position_update',
  TRADE_EXECUTION: 'trade_execution',
  PNL_UPDATE: 'pnl_update',
  ALERT: 'alert',
  HEALTH_UPDATE: 'health_update',
} as const;

export type WebSocketMessageTypeValue = (typeof WebSocketMessageType)[keyof typeof WebSocketMessageType];

// Payload type definitions for known message types

export interface FollowerUpdateData {
  total: number;
  active: number;
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

export interface PositionUpdateData {
  follower_id: string;
  positions: any[];
}

export interface TradeExecutionData {
  trade_id: string;
  follower_id: string;
  action: string;
  symbol: string;
  quantity: number;
  price: number;
  timestamp: string;
}

export interface PnlUpdateData {
  follower_id?: string;
  pnl: number;
  timestamp: string;
}

export interface AlertData {
  type: string;
  severity: string;
  message: string;
  timestamp: string;
  follower_id?: string;
}

export interface HealthUpdateData {
  service: string;
  status: 'healthy' | 'unhealthy' | 'degraded';
  timestamp: string;
}