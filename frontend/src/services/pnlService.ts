import apiClient from './api';
import { 
  DailyPnlSchema,
  MonthlyPnlSchema,
  FollowerPnlArraySchema,
  type DailyPnl,
  type MonthlyPnl,
  type FollowerPnlArray
} from '../schemas/pnl.schema';

// Get today's P&L (new format - returns array of follower P&L)
export const getPnlToday = async (): Promise<FollowerPnlArray> => {
  try {
    const response = await apiClient.get('/pnl/today');
    // Validate response data with Zod
    const validatedData = FollowerPnlArraySchema.parse(response.data);
    return validatedData;
  } catch (error) {
    console.error('Failed to fetch today\'s P&L:', error);
    if (error && typeof error === 'object' && 'issues' in error) {
      console.error('Validation errors:', (error as any).issues);
    }
    throw error;
  }
};

// Get monthly P&L (new format - returns array of follower P&L)
export const getPnlMonth = async (year?: number, month?: number): Promise<FollowerPnlArray> => {
  try {
    const params: any = {};
    if (year) params.year = year;
    if (month) params.month = month;
    
    const response = await apiClient.get('/pnl/month', { params });
    // Validate response data with Zod
    const validatedData = FollowerPnlArraySchema.parse(response.data);
    return validatedData;
  } catch (error) {
    console.error('Failed to fetch monthly P&L:', error);
    if (error && typeof error === 'object' && 'issues' in error) {
      console.error('Validation errors:', (error as any).issues);
    }
    throw error;
  }
};

// Legacy functions for backward compatibility
export const getTodayPnl = async (): Promise<DailyPnl> => {
  try {
    const response = await apiClient.get('/pnl/today');
    // Validate response data with Zod
    const validatedData = DailyPnlSchema.parse(response.data);
    return validatedData;
  } catch (error) {
    console.error('Failed to fetch today\'s P&L:', error);
    if (error && typeof error === 'object' && 'issues' in error) {
      console.error('Validation errors:', (error as any).issues);
    }
    throw error;
  }
};

export const getMonthlyPnl = async (year?: number, month?: number): Promise<MonthlyPnl> => {
  try {
    const params: any = {};
    if (year) params.year = year;
    if (month) params.month = month;
    
    const response = await apiClient.get('/pnl/month', { params });
    // Validate response data with Zod
    const validatedData = MonthlyPnlSchema.parse(response.data);
    return validatedData;
  } catch (error) {
    console.error('Failed to fetch monthly P&L:', error);
    if (error && typeof error === 'object' && 'issues' in error) {
      console.error('Validation errors:', (error as any).issues);
    }
    throw error;
  }
};

// Get P&L for a specific date range (utility function)
export const getPnlRange = async (startDate: Date, endDate: Date): Promise<DailyPnl[]> => {
  try {
    const startYear = startDate.getFullYear();
    const startMonth = startDate.getMonth() + 1;
    const endYear = endDate.getFullYear();
    const endMonth = endDate.getMonth() + 1;
    
    const monthlyData: MonthlyPnl[] = [];
    
    // Fetch all months in the range
    for (let year = startYear; year <= endYear; year++) {
      const monthStart = year === startYear ? startMonth : 1;
      const monthEnd = year === endYear ? endMonth : 12;
      
      for (let month = monthStart; month <= monthEnd; month++) {
        const data = await getMonthlyPnl(year, month);
        monthlyData.push(data);
      }
    }
    
    // Flatten and filter daily data
    const allDailyData = monthlyData.flatMap(m => m.daily_breakdown);
    
    return allDailyData.filter(d => {
      const date = new Date(d.date);
      return date >= startDate && date <= endDate;
    });
  } catch (error) {
    console.error('Failed to fetch P&L range:', error);
    throw error;
  }
};

// Calculate total P&L for a period
export const calculatePeriodPnl = async (days: number = 30): Promise<{
  total: number;
  realized: number;
  unrealized: number;
  dailyAverage: number;
}> => {
  try {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);
    
    const dailyData = await getPnlRange(startDate, endDate);
    
    const total = dailyData.reduce((sum, day) => sum + day.total_pnl, 0);
    const realized = dailyData.reduce((sum, day) => sum + day.realized_pnl, 0);
    const unrealized = dailyData.reduce((sum, day) => sum + day.unrealized_pnl, 0);
    const dailyAverage = dailyData.length > 0 ? total / dailyData.length : 0;
    
    return {
      total,
      realized,
      unrealized,
      dailyAverage
    };
  } catch (error) {
    console.error('Failed to calculate period P&L:', error);
    throw error;
  }
};