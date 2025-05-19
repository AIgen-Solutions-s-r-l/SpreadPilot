import React from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  Box, 
  Button,
  List,
  ListItem,
  Divider,
  useTheme
} from '@mui/material';
import { 
  TrendingUp as TrendingUpIcon,
  ArrowForward as ArrowForwardIcon,
  ArrowCircleUp as ArrowCircleUpIcon,
  ArrowCircleDown as ArrowCircleDownIcon,
  Warning as WarningIcon
} from '@mui/icons-material';

// Mock data for trading activities
const mockActivities = [
  { 
    time: '12:34 PM', 
    followerId: 'Follower_001', 
    action: 'Opened position', 
    symbol: 'SOXL', 
    details: '100 shares @ $45.67' 
  },
  { 
    time: '12:15 PM', 
    followerId: 'Follower_003', 
    action: 'Closed position', 
    symbol: 'SOXS', 
    details: '50 shares @ $32.10' 
  },
  { 
    time: '11:45 AM', 
    followerId: 'Follower_002', 
    action: 'Adjusted stop loss', 
    symbol: 'SOXL', 
    details: '@ $44.20' 
  },
  { 
    time: '11:30 AM', 
    followerId: 'Follower_005', 
    action: 'Opened position', 
    symbol: 'SOXS', 
    details: '75 shares @ $31.45' 
  },
  { 
    time: '10:15 AM', 
    followerId: 'Follower_001', 
    action: 'Closed position', 
    symbol: 'SOXL', 
    details: '50 shares @ $46.78' 
  },
];

interface ActivityItemProps {
  activity: {
    time: string;
    followerId: string;
    action: string;
    symbol: string;
    details: string;
  };
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
    <ListItem 
      sx={{ 
        position: 'relative',
        pl: 6,
        pr: 2,
        py: 2,
        animation: 'fadeIn 0.5s ease-in-out',
        animationDelay: `${index * 0.1}s`,
        animationFillMode: 'both',
        '@keyframes fadeIn': {
          '0%': {
            opacity: 0,
            transform: 'translateY(10px)'
          },
          '100%': {
            opacity: 1,
            transform: 'translateY(0)'
          }
        }
      }}
    >
      {/* Timeline dot */}
      <Box 
        sx={{ 
          position: 'absolute',
          left: 16,
          top: '50%',
          transform: 'translateY(-50%)',
          width: 32,
          height: 32,
          borderRadius: '50%',
          bgcolor: 'primary.50',
          border: '2px solid',
          borderColor: 'primary.200',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1
        }}
      >
        {getActionIcon()}
      </Box>
      
      {/* Timeline line */}
      <Box 
        sx={{ 
          position: 'absolute',
          left: 31,
          top: 0,
          bottom: 0,
          width: 2,
          bgcolor: 'divider',
          zIndex: 0
        }}
      />
      
      {/* Time */}
      <Box 
        sx={{ 
          position: 'absolute',
          left: 0,
          top: '50%',
          transform: 'translateY(-50%)',
          width: 16,
          textAlign: 'right',
          pr: 1,
          fontSize: '0.75rem',
          color: 'text.secondary'
        }}
      >
        {activity.time}
      </Box>
      
      {/* Content */}
      <Box 
        sx={{ 
          p: 2,
          borderRadius: 2,
          border: '1px solid',
          borderColor: 'divider',
          width: '100%',
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
            {activity.followerId}
          </Typography>
          <Typography variant="subtitle2" fontWeight="medium" color="primary.main">
            {activity.symbol}
          </Typography>
        </Box>
        
        <Box display="flex" alignItems="center">
          <Typography 
            variant="body2" 
            fontWeight="medium"
            sx={{ color: getActionColor() }}
          >
            {activity.action}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>
            {activity.details}
          </Typography>
        </Box>
      </Box>
    </ListItem>
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
        
        <List disablePadding sx={{ position: 'relative' }}>
          {mockActivities.map((activity, index) => (
            <ActivityItem key={`${activity.time}-${activity.followerId}`} activity={activity} index={index} />
          ))}
        </List>
      </CardContent>
    </Card>
  );
};

export default TradingActivityTimeline;