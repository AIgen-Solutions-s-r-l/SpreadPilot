import React from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  Box, 
  Button,
  List,
  ListItem,
  Avatar,
  useTheme
} from '@mui/material';
import { 
  Notifications as NotificationsIcon,
  ArrowForward as ArrowForwardIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  AccessTime as AccessTimeIcon
} from '@mui/icons-material';

// Mock data for alerts
const mockAlerts = [
  {
    type: 'warning' as const,
    time: '12:45 PM',
    message: 'Connection to IB Gateway temporarily lost for Follower_004'
  },
  {
    type: 'success' as const,
    time: '12:30 PM',
    message: 'System backup completed successfully'
  },
  {
    type: 'info' as const,
    time: '11:50 AM',
    message: 'New trading signal detected from Google Sheets'
  },
  {
    type: 'warning' as const,
    time: '10:20 AM',
    message: 'High volatility detected for SOXL'
  },
  {
    type: 'success' as const,
    time: '09:30 AM',
    message: 'Trading day started - all systems operational'
  },
];

interface AlertItemProps {
  alert: {
    type: 'warning' | 'success' | 'info' | 'error';
    time: string;
    message: string;
  };
  index: number;
}

const AlertItem: React.FC<AlertItemProps> = ({ alert, index }) => {
  const theme = useTheme();
  
  const getAlertIcon = () => {
    switch (alert.type) {
      case 'warning':
        return <WarningIcon sx={{ color: theme.palette.warning.main }} />;
      case 'success':
        return <CheckCircleIcon sx={{ color: theme.palette.success.main }} />;
      case 'info':
        return <InfoIcon sx={{ color: theme.palette.info.main }} />;
      case 'error':
        return <ErrorIcon sx={{ color: theme.palette.error.main }} />;
      default:
        return <InfoIcon sx={{ color: theme.palette.info.main }} />;
    }
  };
  
  const getAlertColor = () => {
    switch (alert.type) {
      case 'warning': return theme.palette.warning.main;
      case 'success': return theme.palette.success.main;
      case 'info': return theme.palette.info.main;
      case 'error': return theme.palette.error.main;
      default: return theme.palette.info.main;
    }
  };
  
  const getAlertBgColor = () => {
    switch (alert.type) {
      case 'warning': return theme.palette.warning.light;
      case 'success': return theme.palette.success.light;
      case 'info': return theme.palette.info.light;
      case 'error': return theme.palette.error.light;
      default: return theme.palette.info.light;
    }
  };
  
  return (
    <ListItem 
      sx={{ 
        p: 2, 
        borderRadius: 2, 
        border: '1px solid',
        borderColor: 'divider',
        mb: 1.5,
        transition: 'all 0.2s',
        '&:hover': {
          bgcolor: 'action.hover',
          transform: 'translateY(-2px)',
          boxShadow: 1,
        },
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
      <Box sx={{ display: 'flex', width: '100%' }}>
        <Avatar 
          sx={{ 
            bgcolor: getAlertBgColor(),
            color: getAlertColor(),
            width: 40,
            height: 40,
            mr: 2
          }}
        >
          {getAlertIcon()}
        </Avatar>
        
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="body2" fontWeight="medium" color="text.primary" gutterBottom>
            {alert.message}
          </Typography>
          
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <AccessTimeIcon sx={{ fontSize: 14, color: 'text.secondary', mr: 0.5 }} />
            <Typography variant="caption" color="text.secondary">
              {alert.time}
            </Typography>
          </Box>
        </Box>
      </Box>
    </ListItem>
  );
};

interface RecentAlertsProps {
  title?: string;
  onViewAll?: () => void;
}

const RecentAlerts: React.FC<RecentAlertsProps> = ({ 
  title = 'RECENT ALERTS',
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
            <NotificationsIcon color="primary" sx={{ mr: 1 }} />
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
        
        <List disablePadding>
          {mockAlerts.map((alert, index) => (
            <AlertItem key={`${alert.time}-${index}`} alert={alert} index={index} />
          ))}
        </List>
      </CardContent>
    </Card>
  );
};

export default RecentAlerts;