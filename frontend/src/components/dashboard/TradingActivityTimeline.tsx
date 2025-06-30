import React, { useEffect, useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  useTheme,
  Paper
} from '@mui/material';
import {
  Timeline,
  TimelineItem,
  TimelineSeparator,
  TimelineConnector,
  TimelineContent,
  TimelineDot,
  TimelineOppositeContent,
  timelineOppositeContentClasses,
} from '@mui/lab';
import {
  TrendingUp as TrendingUpIcon,
  ArrowForward as ArrowForwardIcon,
  ArrowCircleUp as ArrowCircleUpIcon,
  ArrowCircleDown as ArrowCircleDownIcon,
  Warning as WarningIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import tradingActivityService, { TradingActivity } from '../../services/tradingActivityService';

// Helper function to format activity details
const formatActivityDetails = (activity: TradingActivity): string => {
  const qty = activity.quantity || 0;
  const price = activity.price || 0;
  const contractType = activity.contract_type;
  const strike = activity.strike;
  
  if (contractType && strike) {
    return `${qty} ${strike}${contractType} @ $${price.toFixed(2)}`;
  }
  return `${qty} shares @ $${price.toFixed(2)}`;
};

// Helper function to format action text
const formatAction = (action: string): string => {
  switch (action) {
    case 'OPENED':
      return 'Opened position';
    case 'CLOSED':
      return 'Closed position';
    case 'ADJUSTED':
      return 'Adjusted position';
    case 'EXECUTED':
      return 'Executed trade';
    default:
      return action;
  }
};

interface ActivityItemProps {
  activity: TradingActivity;
  index: number;
}

const ActivityItem: React.FC<ActivityItemProps> = ({ activity, index }) => {
  const theme = useTheme();
  
  const getActionColor = () => {
    if (activity.action.includes('Opened')) return theme.palette.trading.buy;
    if (activity.action.includes('Closed')) return theme.palette.trading.sell;
    return theme.palette.warning.main;
  };
  
  const getActionIcon = () => {
    if (activity.action.includes('Opened')) {
      return <ArrowCircleUpIcon sx={{ fontSize: 16, color: theme.palette.trading.buy }} />;
    }
    if (activity.action.includes('Closed')) {
      return <ArrowCircleDownIcon sx={{ fontSize: 16, color: theme.palette.trading.sell }} />;
    }
    return <WarningIcon sx={{ fontSize: 16, color: theme.palette.warning.main }} />;
  };
  
  return (
    <TimelineItem
      sx={{
        animation: 'fadeIn 0.5s ease-in-out',
        animationDelay: `${index * 0.1}s`,
        animationFillMode: 'both',
        '@keyframes fadeIn': {
          '0%': { opacity: 0, transform: 'translateY(10px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' }
        },
        '&::before': { // Removes the default opposite content padding if not used
          flex: 0.1, // Adjust flex to control space for time, or remove if time is part of TimelineDot
          padding: 0,
        }
      }}
    >
      <TimelineOppositeContent
        sx={{
          m: 'auto 0',
          flex: 0.2, // Give a bit more space for time
          textAlign: 'right',
          pr: 2, // Add padding to separate from the line
        }}
        align="right"
        variant="body2"
        color="text.secondary"
      >
        {activity.time}
      </TimelineOppositeContent>
      <TimelineSeparator>
        <TimelineConnector sx={{ bgcolor: 'divider' }} />
        <TimelineDot
          variant="outlined"
          sx={{
            borderColor: 'primary.200',
            bgcolor: 'primary.50',
            p: 0.5
          }}
        >
          {getActionIcon()}
        </TimelineDot>
        <TimelineConnector sx={{ bgcolor: 'divider' }} />
      </TimelineSeparator>
      <TimelineContent sx={{ py: '12px', px: 2 }}>
        <Paper
          elevation={0}
          sx={{
            p: 2,
            borderRadius: 2,
            border: '1px solid',
            borderColor: 'divider',
            transition: 'all 0.2s',
            '&:hover': {
              bgcolor: 'action.hover',
              transform: 'translateY(-2px)',
              boxShadow: 1,
            },
           }}
        >
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
            <Typography variant="subtitle2" fontWeight="medium">
              {activity.follower_name || activity.follower_id}
            </Typography>
            <Typography variant="subtitle2" fontWeight="medium" color="primary.main">
              {activity.symbol}
            </Typography>
          </Box>
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Box display="flex" alignItems="center">
              <Typography
                variant="body2"
                fontWeight="medium"
                sx={{ color: getActionColor() }}
              >
                {formatAction(activity.action)}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>
                {formatActivityDetails(activity)}
              </Typography>
            </Box>
            {activity.pnl !== undefined && (
              <Typography 
                variant="body2" 
                sx={{ 
                  color: activity.pnl >= 0 ? theme.palette.success.main : theme.palette.error.main,
                  fontWeight: 600,
                  ml: 1
                }}
              >
                {activity.pnl >= 0 ? '+' : ''}${activity.pnl.toFixed(2)}
              </Typography>
            )}
          </Box>
        </Paper>
      </TimelineContent>
    </TimelineItem>
  );
};

interface TradingActivityTimelineProps {
  title?: string;
  onViewAll?: () => void;
}

const TradingActivityTimeline: React.FC<TradingActivityTimelineProps> = ({ 
  title = 'TRADING ACTIVITY',
  onViewAll 
}) => {
  const [activities, setActivities] = useState<TradingActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchActivities = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await tradingActivityService.getRecentActivities(10);
      setActivities(data);
    } catch (err) {
      console.error('Failed to fetch trading activities:', err);
      setError('Failed to load trading activities');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActivities();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchActivities, 30000);
    
    return () => clearInterval(interval);
  }, []);

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
            <TrendingUpIcon color="primary" sx={{ mr: 1 }} />
            <Typography variant="h6" component="h3" fontWeight="medium">
              {title}
            </Typography>
          </Box>
          
          <Box display="flex" gap={1}>
            <Button
              size="small"
              onClick={fetchActivities}
              disabled={loading}
              sx={{ 
                minWidth: 'auto',
                p: 1,
                color: 'text.secondary',
                '&:hover': {
                  bgcolor: 'action.hover',
                }
              }}
            >
              <RefreshIcon sx={{ fontSize: 18 }} />
            </Button>
            <Button
              size="small"
              endIcon={<ArrowForwardIcon />}
              onClick={onViewAll}
              sx={{ 
                fontSize: '0.75rem',
                fontWeight: 'medium',
                color: 'primary.main',
                '&:hover': {
                  bgcolor: 'primary.50',
                }
              }}
            >
              VIEW ALL
            </Button>
          </Box>
        </Box>
        {loading ? (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight={300}>
            <Typography variant="body2" color="text.secondary">
              Loading activities...
            </Typography>
          </Box>
        ) : error ? (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight={300}>
            <Typography variant="body2" color="error">
              {error}
            </Typography>
          </Box>
        ) : activities.length === 0 ? (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight={300}>
            <Typography variant="body2" color="text.secondary">
              No recent trading activity
            </Typography>
          </Box>
        ) : (
          <Timeline
            sx={{
              p:0, // Remove default padding from Timeline
              [`& .${timelineOppositeContentClasses.root}`]: {
                flex: 0.2, // Control width of opposite content (time)
              },
            }}
          >
            {activities.map((activity, index) => (
              <ActivityItem 
                key={activity.id || `${activity.timestamp}-${activity.follower_id}-${index}`} 
                activity={activity} 
                index={index} 
              />
            ))}
          </Timeline>
        )}
      </CardContent>
    </Card>
  );
};

export default TradingActivityTimeline;