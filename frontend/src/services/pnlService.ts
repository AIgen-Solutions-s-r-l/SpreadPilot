import apiClient from './api';
import { 
  DailyPnlSchema,
  MonthlyPnlSchema,
  type DailyPnl,
  type MonthlyPnl
} from '../schemas/pnl.schema';

// Get today's P&L
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

// Get monthly P&L
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

// Get P&L history formatted for chart display
export const getPnLHistory = async (timeRange: string): Promise<Array<{ time: string; value: number }>> => {
  try {
    const endDate = new Date();
    const startDate = new Date();
    let data: Array<{ time: string; value: number }> = [];
    
    switch (timeRange) {
      case '1D': {
        // Get today's hourly data (mock for now, as API doesn't provide hourly)
        const todayPnl = await getTodayPnl();
        const baseValue = todayPnl.total_pnl;
        const hours = ['9:30', '10:30', '11:30', '12:30', '13:30', '14:30', '15:30', '16:00'];
        data = hours.map((hour, index) => ({
          time: hour,
          value: baseValue * (index + 1) / hours.length
        }));
        break;
      }
      
      case '1W': {
        // Get last 7 days
        startDate.setDate(startDate.getDate() - 7);
        const dailyData = await getPnlRange(startDate, endDate);
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        
        data = dailyData.map(day => ({
          time: dayNames[new Date(day.date).getDay()],
          value: day.total_pnl
        }));
        break;
      }
      
      case '1M': {
        // Get last 30 days grouped by week
        startDate.setDate(startDate.getDate() - 30);
        const dailyData = await getPnlRange(startDate, endDate);
        
        // Group by week
        const weeks: { [key: string]: number } = {};
        dailyData.forEach(day => {
          const date = new Date(day.date);
          const weekNum = Math.floor((date.getDate() - 1) / 7) + 1;
          const weekKey = `Week ${weekNum}`;
          weeks[weekKey] = (weeks[weekKey] || 0) + day.total_pnl;
        });
        
        data = Object.entries(weeks).map(([time, value]) => ({ time, value }));
        break;
      }
      
      case '3M': {
        // Get last 3 months
        startDate.setMonth(startDate.getMonth() - 3);
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        
        const monthlyTotals: { [key: string]: number } = {};
        for (let i = 0; i < 3; i++) {
          const targetDate = new Date(endDate);
          targetDate.setMonth(targetDate.getMonth() - i);
          const monthData = await getMonthlyPnl(targetDate.getFullYear(), targetDate.getMonth() + 1);
          const monthName = monthNames[targetDate.getMonth()];
          monthlyTotals[monthName] = monthData.total_pnl;
        }
        
        data = Object.entries(monthlyTotals)
          .reverse()
          .map(([time, value]) => ({ time, value }));
        break;
      }
      
      case 'YTD': {
        // Get year-to-date by month
        const currentYear = endDate.getFullYear();
        startDate.setMonth(0);
        startDate.setDate(1);
        
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const currentMonth = endDate.getMonth();
        
        for (let month = 0; month <= currentMonth; month++) {
          const monthData = await getMonthlyPnl(currentYear, month + 1);
          data.push({
            time: monthNames[month],
            value: monthData.total_pnl
          });
        }
        break;
      }
      
      case '1Y': {
        // Get last 12 months
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        
        for (let i = 11; i >= 0; i--) {
          const targetDate = new Date(endDate);
          targetDate.setMonth(targetDate.getMonth() - i);
          const monthData = await getMonthlyPnl(targetDate.getFullYear(), targetDate.getMonth() + 1);
          const monthName = monthNames[targetDate.getMonth()];
          data.push({
            time: monthName,
            value: monthData.total_pnl
          });
        }
        break;
      }
      
      case 'ALL': {
        // Get all available years
        const currentYear = endDate.getFullYear();
        const startYear = currentYear - 3; // Show last 4 years
        
        for (let year = startYear; year <= currentYear; year++) {
          let yearTotal = 0;
          const monthEnd = year === currentYear ? endDate.getMonth() + 1 : 12;
          
          for (let month = 1; month <= monthEnd; month++) {
            try {
              const monthData = await getMonthlyPnl(year, month);
              yearTotal += monthData.total_pnl;
            } catch (_error) {
              // Skip months without data
            }
          }
          
          if (yearTotal !== 0) {
            data.push({
              time: year.toString(),
              value: yearTotal
            });
          }
        }
        break;
      }
      
      default: {
        // Default to 1M
        return getPnLHistory('1M');
      }
    }
    
    // Ensure cumulative values for better visualization
    let cumulative = 0;
    data = data.map(item => {
      cumulative += item.value;
      return { ...item, value: cumulative };
    });
    
    return data;
  } catch (error) {
    console.error('Failed to get P&L history:', error);
    // Return empty array on error
    return [];
  }
};