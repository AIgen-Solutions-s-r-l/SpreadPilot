import React from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  Box, 
  Button,
  List,
  ListItem,
  useTheme,
  Skeleton
} from '@mui/material';
import { 
  People as PeopleIcon,
  ArrowForward as ArrowForwardIcon
} from '@mui/icons-material';
import type { Follower } from '../../schemas/follower.schema';

interface StatusIndicatorProps {
  status: 'online' | 'offline' | 'warning' | 'error';
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ status }) => {
  const getStatusColor = () => {
    switch (status) {
      case 'online': return 'success.main';
      case 'offline': return 'text.disabled';
      case 'warning': return 'warning.main';
      case 'error': return 'error.main';
      default: return 'text.disabled';
    }
  };
  
  return (
    <Box
      component="span"
      sx={{
        display: 'inline-block',
        width: 8,
        height: 8,
        borderRadius: '50%',
        bgcolor: getStatusColor(),
        mr: 1.5,
        boxShadow: '0 0 0 2px #fff',
      }}
    />
  );
};

interface FollowerItemProps {
  follower: Follower;
}

const FollowerItem: React.FC<FollowerItemProps> = ({ follower }) => {
  const theme = useTheme();
  
  const getPnlColor = () => {
    if (follower.pnlToday > 0) return theme.palette.trading.profit;
    if (follower.pnlToday < 0) return theme.palette.trading.loss;
    return theme.palette.trading.neutral;
  };
  
  // Map follower status to display status
  const getDisplayStatus = (): 'online' | 'offline' | 'warning' | 'error' => {
    if (!follower.enabled) return 'offline';
    if (follower.botStatus === 'ERROR' || follower.ibGwStatus === 'ERROR') return 'error';
    if (follower.botStatus === 'STARTING' || follower.ibGwStatus === 'CONNECTING') return 'warning';
    if (follower.botStatus === 'RUNNING' && follower.ibGwStatus === 'CONNECTED') return 'online';
    return 'offline';
  };

  // Format P&L
  const formatPnl = (value: number) => {
    const isNegative = value < 0;
    return `${isNegative ? '-' : '+'}$${Math.abs(value).toFixed(2)}`;
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
      <Box sx={{ width: '100%' }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
          <Box display="flex" alignItems="center">
            <StatusIndicator status={getDisplayStatus()} />
            <Typography variant="subtitle2" fontWeight="medium">
              {follower.id}
            </Typography>
          </Box>
          <Typography 
            variant="subtitle2" 
            fontWeight="medium"
            sx={{ color: getPnlColor() }}
          >
            {formatPnl(follower.pnlToday)}
          </Typography>
        </Box>
        
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="caption" color="text.secondary">
            Positions: {follower.positions?.count || 0}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            TV: ${follower.timeValue?.toFixed(2) || '0.00'}
          </Typography>
        </Box>
      </Box>
    </ListItem>
  );
};

interface ActiveFollowersListProps {
  title?: string;
  followers?: Follower[];
  loading?: boolean;
  onViewAll?: () => void;
}

const ActiveFollowersListV2: React.FC<ActiveFollowersListProps> = ({ 
  title = 'ACTIVE FOLLOWERS',
  followers = [],
  loading = false,
  onViewAll 
}) => {
  // Show only the first 5 active followers
  const displayFollowers = followers.filter(f => f.enabled).slice(0, 5);

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
            <PeopleIcon color="primary" sx={{ mr: 1 }} />
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
                <Box sx={{ width: '100%' }}>
                  <Skeleton variant="text" width="60%" height={24} />
                  <Skeleton variant="text" width="40%" height={20} />
                </Box>
              </ListItem>
            ))
          ) : displayFollowers.length > 0 ? (
            displayFollowers.map((follower) => (
              <FollowerItem key={follower.id} follower={follower} />
            ))
          ) : (
            <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 4 }}>
              No active followers found
            </Typography>
          )}
        </List>
      </CardContent>
    </Card>
  );
};

export default ActiveFollowersListV2;