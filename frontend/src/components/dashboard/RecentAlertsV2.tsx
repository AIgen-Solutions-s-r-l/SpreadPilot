import React from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  Box, 
  Button,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  useTheme,
  Skeleton
} from '@mui/material';
import { 
  Warning as WarningIcon,
  ArrowForward as ArrowForwardIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  BugReport as BugReportIcon,
  ErrorOutline as CriticalIcon,
} from '@mui/icons-material';
import type { LogEntry } from '../../schemas/log.schema';
import { LogLevel } from '../../schemas/log.schema';

interface AlertItemProps {
  log: LogEntry;
}

const AlertItem: React.FC<AlertItemProps> = ({ log }) => {
  const theme = useTheme();
  
  const getAlertIcon = () => {
    switch (log.level) {
      case LogLevel.CRITICAL:
        return <CriticalIcon sx={{ color: theme.palette.error.dark }} />;
      case LogLevel.ERROR:
        return <ErrorIcon sx={{ color: theme.palette.error.main }} />;
      case LogLevel.WARNING:
        return <WarningIcon sx={{ color: theme.palette.warning.main }} />;
      case LogLevel.INFO:
        return <InfoIcon sx={{ color: theme.palette.info.main }} />;
      case LogLevel.DEBUG:
        return <BugReportIcon sx={{ color: theme.palette.grey[600] }} />;
      default:
        return <InfoIcon sx={{ color: theme.palette.text.secondary }} />;
    }
  };
  
  const getTimeDifference = (timestamp: string) => {
    const now = new Date();
    const logTime = new Date(timestamp);
    const diffMs = now.getTime() - logTime.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffDays > 0) return `${diffDays}d ago`;
    if (diffHours > 0) return `${diffHours}h ago`;
    if (diffMins > 0) return `${diffMins}m ago`;
    return 'just now';
  };
  
  // Truncate message if too long
  const truncateMessage = (message: string, maxLength: number = 80) => {
    if (message.length <= maxLength) return message;
    return message.substring(0, maxLength) + '...';
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
      }}
    >
      <ListItemIcon sx={{ minWidth: 40 }}>
        {getAlertIcon()}
      </ListItemIcon>
      <ListItemText
        primary={
          <Typography variant="body2" fontWeight="medium">
            {truncateMessage(log.message)}
          </Typography>
        }
        secondary={
          <Box display="flex" justifyContent="space-between" alignItems="center" mt={0.5}>
            <Typography variant="caption" color="text.secondary">
              {log.service}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {getTimeDifference(log.timestamp)}
            </Typography>
          </Box>
        }
      />
    </ListItem>
  );
};

interface RecentAlertsProps {
  title?: string;
  logs?: LogEntry[];
  loading?: boolean;
  onViewAll?: () => void;
}

const RecentAlertsV2: React.FC<RecentAlertsProps> = ({ 
  title = 'RECENT ALERTS',
  logs = [],
  loading = false,
  onViewAll 
}) => {
  // Filter for important logs (ERROR, WARNING, CRITICAL) and show only the first 5
  const alertLogs = logs
    .filter(log => 
      log.level === LogLevel.ERROR || 
      log.level === LogLevel.WARNING || 
      log.level === LogLevel.CRITICAL
    )
    .slice(0, 5);

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
            <WarningIcon color="warning" sx={{ mr: 1 }} />
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
          {loading ? (
            // Show skeletons while loading
            Array.from({ length: 5 }).map((_, index) => (
              <ListItem key={index} sx={{ p: 2, mb: 1.5 }}>
                <ListItemIcon sx={{ minWidth: 40 }}>
                  <Skeleton variant="circular" width={24} height={24} />
                </ListItemIcon>
                <Box sx={{ width: '100%' }}>
                  <Skeleton variant="text" width="80%" height={20} />
                  <Skeleton variant="text" width="60%" height={16} />
                </Box>
              </ListItem>
            ))
          ) : alertLogs.length > 0 ? (
            alertLogs.map((log) => (
              <AlertItem key={log.id} log={log} />
            ))
          ) : (
            <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 4 }}>
              No recent alerts
            </Typography>
          )}
        </List>
      </CardContent>
    </Card>
  );
};

export default RecentAlertsV2;