import React, { useState, useEffect } from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  Box, 
  ToggleButtonGroup, 
  ToggleButton,
  useTheme,
  Skeleton
} from '@mui/material';
import { 
  BarChart as BarChartIcon
} from '@mui/icons-material';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { getPnLHistory } from '../../services/pnlService';

// Mock data for the chart
const generateChartData = (timeRange: string) => {
  // Different data sets based on time range
  const dataSets: Record<string, Array<{ time: string; value: number }>> = {
    '1D': [
      { time: '9:30', value: 5000 },
      { time: '10:30', value: 5200 },
      { time: '11:30', value: 5100 },
      { time: '12:30', value: 5400 },
      { time: '13:30', value: 5600 },
      { time: '14:30', value: 5500 },
      { time: '15:30', value: 5800 },
      { time: '16:00', value: 6000 },
    ],
    '1W': [
      { time: 'Mon', value: 5000 },
      { time: 'Tue', value: 5200 },
      { time: 'Wed', value: 5500 },
      { time: 'Thu', value: 5700 },
      { time: 'Fri', value: 6000 },
    ],
    '1M': [
      { time: 'Week 1', value: 5000 },
      { time: 'Week 2', value: 5500 },
      { time: 'Week 3', value: 6000 },
      { time: 'Week 4', value: 7000 },
    ],
    '3M': [
      { time: 'Jan', value: 5000 },
      { time: 'Feb', value: 6000 },
      { time: 'Mar', value: 7500 },
    ],
    'YTD': [
      { time: 'Jan', value: 5000 },
      { time: 'Feb', value: 5500 },
      { time: 'Mar', value: 6000 },
      { time: 'Apr', value: 7000 },
      { time: 'May', value: 7500 },
    ],
    '1Y': [
      { time: 'Jun', value: 5000 },
      { time: 'Jul', value: 5200 },
      { time: 'Aug', value: 5500 },
      { time: 'Sep', value: 5300 },
      { time: 'Oct', value: 5600 },
      { time: 'Nov', value: 6000 },
      { time: 'Dec', value: 6200 },
      { time: 'Jan', value: 6500 },
      { time: 'Feb', value: 7000 },
      { time: 'Mar', value: 7200 },
      { time: 'Apr', value: 7500 },
      { time: 'May', value: 8000 },
    ],
    'ALL': [
      { time: '2022', value: 3000 },
      { time: '2023', value: 5000 },
      { time: '2024', value: 6500 },
      { time: '2025', value: 8000 },
    ],
  };
  
  return dataSets[timeRange] || dataSets['1M'];
};

// Custom tooltip component
interface TooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; color: string }>;
  label?: string;
}

const CustomTooltip = ({ active, payload, label }: TooltipProps) => {
  if (active && payload && payload.length) {
    return (
      <Box
        sx={{
          bgcolor: 'background.paper',
          p: 2,
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 1,
          boxShadow: 2,
        }}
      >
        <Typography variant="subtitle2" color="text.primary">
          {label}
        </Typography>
        <Typography variant="body2" color="primary.main" fontWeight="medium">
          ${payload[0].value.toLocaleString()}
        </Typography>
      </Box>
    );
  }
  
  return null;
};

interface PerformanceChartProps {
  title?: string;
  pnlHistory?: Array<{ date: string; value: number }>;
}

const PerformanceChart: React.FC<PerformanceChartProps> = ({ 
  title = 'PERFORMANCE', 
  pnlHistory = [] 
}) => {
  const [timeRange, setTimeRange] = useState('1M');
  const [data, setData] = useState<Array<{ time: string; value: number }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const theme = useTheme();
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Use prop data if available, otherwise fetch from service
        if (pnlHistory.length > 0) {
          setData(pnlHistory.map(item => ({ time: item.date, value: item.value })));
        } else {
          const historyData = await getPnLHistory(timeRange);
          if (historyData.length === 0) {
            // Fallback to mock data if no real data available
            setData(generateChartData(timeRange));
          } else {
            setData(historyData);
          }
        }
      } catch (err) {
        console.error('Failed to fetch P&L data:', err);
        setError('Failed to load P&L data');
        // Use mock data on error
        setData(generateChartData(timeRange));
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [timeRange, pnlHistory]);
  
  const handleTimeRangeChange = (
    _event: React.MouseEvent<HTMLElement>,
    newTimeRange: string,
  ) => {
    if (newTimeRange !== null) {
      setTimeRange(newTimeRange);
    }
  };
  
  // Calculate min and max for YAxis
  const minValue = Math.min(...data.map(item => item.value)) * 0.9;
  const maxValue = Math.max(...data.map(item => item.value)) * 1.1;
  
  return (
    <Card 
      sx={{ 
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        transition: 'transform 0.3s, box-shadow 0.3s',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: (theme) => theme.shadows[4],
        }
      }}
    >
      <CardContent sx={{ flexGrow: 1, p: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Box display="flex" alignItems="center">
            <BarChartIcon color="primary" sx={{ mr: 1 }} />
            <Typography variant="h6" component="h3" fontWeight="medium">
              {title}
            </Typography>
          </Box>
          
          <ToggleButtonGroup
            value={timeRange}
            exclusive
            onChange={handleTimeRangeChange}
            size="small"
            aria-label="time range"
            sx={{
              bgcolor: 'action.hover',
              borderRadius: 2,
              '& .MuiToggleButton-root': {
                border: 'none',
                px: 1.5,
                py: 0.5,
                fontSize: '0.75rem',
                fontWeight: 'medium',
                '&.Mui-selected': {
                  bgcolor: 'background.paper',
                  color: 'primary.main',
                  boxShadow: 1,
                },
              },
            }}
          >
            <ToggleButton value="1D">1D</ToggleButton>
            <ToggleButton value="1W">1W</ToggleButton>
            <ToggleButton value="1M">1M</ToggleButton>
            <ToggleButton value="3M">3M</ToggleButton>
            <ToggleButton value="YTD">YTD</ToggleButton>
            <ToggleButton value="1Y">1Y</ToggleButton>
            <ToggleButton value="ALL">ALL</ToggleButton>
          </ToggleButtonGroup>
        </Box>
        
        <Box sx={{ height: 300, width: '100%' }}>
          {loading ? (
            <Skeleton variant="rectangular" height={300} sx={{ borderRadius: 1 }} />
          ) : error ? (
            <Box 
              display="flex" 
              justifyContent="center" 
              alignItems="center" 
              height={300}
              sx={{ 
                bgcolor: 'action.hover', 
                borderRadius: 1,
                border: '1px solid',
                borderColor: 'divider'
              }}
            >
              <Typography variant="body2" color="text.secondary">
                {error}
              </Typography>
            </Box>
          ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={data}
              margin={{
                top: 10,
                right: 10,
                left: 0,
                bottom: 0,
              }}
            >
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={theme.palette.primary.main} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={theme.palette.primary.main} stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={theme.palette.divider} />
              <XAxis 
                dataKey="time" 
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
              />
              <YAxis 
                domain={[minValue, maxValue]}
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
                tickFormatter={(value) => `$${value.toLocaleString()}`}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={data[0].value} stroke={theme.palette.divider} strokeDasharray="3 3" />
              <Area 
                type="monotone" 
                dataKey="value" 
                stroke={theme.palette.primary.main} 
                fillOpacity={1}
                fill="url(#colorValue)"
                strokeWidth={2}
                activeDot={{ r: 6, strokeWidth: 0, fill: theme.palette.primary.main }}
              />
            </AreaChart>
          </ResponsiveContainer>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default PerformanceChart;