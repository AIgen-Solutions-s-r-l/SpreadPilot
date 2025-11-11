import { z } from 'zod';
import apiClient from './api';
import { format } from 'date-fns';

// Schema for trading activity
const TradingActivitySchema = z.object({
  id: z.string(),
  timestamp: z.string(), // ISO date string
  time: z.string().optional(), // Formatted time for display
  follower_id: z.string(),
  follower_name: z.string().optional(),
  action: z.enum(['OPENED', 'CLOSED', 'ADJUSTED', 'EXECUTED']),
  symbol: z.string(),
  contract_type: z.enum(['CALL', 'PUT', 'STOCK']).optional(),
  strike: z.number().optional(),
  expiration: z.string().optional(),
  quantity: z.number(),
  price: z.number(),
  side: z.enum(['BUY', 'SELL']),
  details: z.string().optional(),
  pnl: z.number().optional(),
});

export type TradingActivity = z.infer<typeof TradingActivitySchema>;

// Validate activity data
const validateActivity = (data: unknown): TradingActivity | null => {
  try {
    return TradingActivitySchema.parse(data);
  } catch (error) {
    console.error('Invalid activity data:', error);
    return null;
  }
};

// Response schema for future use when API supports dedicated trading activities endpoint
// const TradingActivitiesResponseSchema = z.object({
//   activities: z.array(TradingActivitySchema),
//   total: z.number(),
// });

class TradingActivityService {
  async getRecentActivities(limit: number = 20): Promise<TradingActivity[]> {
    try {
      // First, try to get recent trades from the logs endpoint
      // Since there's no dedicated trading activity endpoint yet, we'll use logs
      const response = await apiClient.get('/logs/', {
        params: {
          limit: limit,
          search: 'trade,executed,filled,order',
          service: 'trading-bot'
        }
      });

      // Transform log entries into trading activities
      const logs = response.data.logs || [];
      const activities: TradingActivity[] = [];
      
      logs.forEach((log: any) => {
        // Parse trade-related log messages
        const message = log.message || '';
        const timestamp = log.timestamp || new Date().toISOString();
        
        // Look for trade execution patterns in log messages
        if (message.toLowerCase().includes('order filled') || 
            message.toLowerCase().includes('trade executed') ||
            message.toLowerCase().includes('position opened') ||
            message.toLowerCase().includes('position closed')) {
          
          // Extract details from structured log data if available
          const extra = log.extra || {};
          
          const activity = validateActivity({
            id: log._id || `${Date.now()}-${Math.random()}`,
            timestamp: timestamp,
            time: format(new Date(timestamp), 'HH:mm'),
            follower_id: extra.follower_id || 'Unknown',
            follower_name: extra.follower_name,
            action: this.parseAction(message),
            symbol: extra.symbol || this.extractSymbol(message) || 'QQQ',
            contract_type: extra.contract_type,
            strike: extra.strike,
            expiration: extra.expiration,
            quantity: extra.quantity || this.extractQuantity(message) || 0,
            price: extra.price || this.extractPrice(message) || 0,
            side: extra.side || this.parseSide(message),
            details: message,
            pnl: extra.pnl,
          });
          
          if (activity) {
            activities.push(activity);
          }
        }
      });

      return activities.slice(0, limit);
    } catch (error) {
      console.error('Error fetching trading activities:', error);
      
      // Return empty array on error
      return [];
    }
  }

  private parseAction(message: string): 'OPENED' | 'CLOSED' | 'ADJUSTED' | 'EXECUTED' {
    const lowerMessage = message.toLowerCase();
    if (lowerMessage.includes('opened') || lowerMessage.includes('open position')) {
      return 'OPENED';
    } else if (lowerMessage.includes('closed') || lowerMessage.includes('close position')) {
      return 'CLOSED';
    } else if (lowerMessage.includes('adjusted') || lowerMessage.includes('modify')) {
      return 'ADJUSTED';
    }
    return 'EXECUTED';
  }

  private parseSide(message: string): 'BUY' | 'SELL' {
    const lowerMessage = message.toLowerCase();
    if (lowerMessage.includes('sell') || lowerMessage.includes('sold')) {
      return 'SELL';
    }
    return 'BUY';
  }

  private extractSymbol(message: string): string | null {
    // Try to extract symbol from message (e.g., "QQQ 450C")
    const symbolMatch = message.match(/\b(QQQ|SPY|IWM)\b/i);
    return symbolMatch ? symbolMatch[1].toUpperCase() : null;
  }

  private extractQuantity(message: string): number | null {
    // Try to extract quantity from message (e.g., "100 shares", "10 contracts")
    const qtyMatch = message.match(/(\d+)\s*(shares?|contracts?|qty)/i);
    return qtyMatch ? parseInt(qtyMatch[1]) : null;
  }

  private extractPrice(message: string): number | null {
    // Try to extract price from message (e.g., "$45.67", "@ 45.67")
    const priceMatch = message.match(/[$@]\s*(\d+\.?\d*)/);
    return priceMatch ? parseFloat(priceMatch[1]) : null;
  }

  // Subscribe to real-time trading activities via WebSocket
  subscribeToActivities(_onActivity: (activity: TradingActivity) => void): () => void {
    // This would be implemented when WebSocket support is added for trading activities
    // For now, return a no-op unsubscribe function
    if (import.meta.env.DEV) {
      console.log('Trading activity subscription not yet implemented');
    }
    return () => {};
  }
}

export default new TradingActivityService();