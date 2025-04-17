// Based on requirements: ID, Enabled, Bot Status, IB GW Status, Assignment State, P&L Today, P&L Month, P&L Total

export enum BotStatus {
  RUNNING = 'RUNNING',
  STOPPED = 'STOPPED',
  ERROR = 'ERROR',
  STARTING = 'STARTING',
  // Add other relevant statuses
}

export enum IbGwStatus {
  CONNECTED = 'CONNECTED',
  DISCONNECTED = 'DISCONNECTED',
  CONNECTING = 'CONNECTING',
  ERROR = 'ERROR',
  // Add other relevant statuses
}

export enum AssignmentState {
  ASSIGNED = 'ASSIGNED',
  UNASSIGNED = 'UNASSIGNED',
  PENDING = 'PENDING',
  // Add other relevant states
}

export interface Follower {
  id: string; // Or number, depending on backend
  enabled: boolean;
  botStatus: BotStatus;
  ibGwStatus: IbGwStatus;
  assignmentState: AssignmentState;
  pnlToday: number; // Assuming number, adjust if string formatting comes from backend
  pnlMonth: number;
  pnlTotal: number;
}