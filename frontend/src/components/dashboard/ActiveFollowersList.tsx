import React from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  Box, 
  Button,
  List,
  ListItem,
  useTheme
} from '@mui/material';
import { 
  People as PeopleIcon,
  ArrowForward as ArrowForwardIcon
} from '@mui/icons-material';

// Mock data for followers
const mockFollowers = [
  { id: 'Follower_001', status: 'online' as const, pnl: '+$1,245.67', positions: 3, lastActive: '2 min ago' },
  { id: 'Follower_002', status: 'online' as const, pnl: '+$867.45', positions: 2, lastActive: '5 min ago' },
  { id: 'Follower_003', status: 'online' as const, pnl: '-$123.45', positions: 1, lastActive: '10 min ago' },
  { id: 'Follower_004', status: 'offline' as const, pnl: '$0.00', positions: 0, lastActive: '1 day ago' },
  { id: 'Follower_005', status: 'warning' as const, pnl: '+$2,345.67', positions: 4, lastActive: '15 min ago' },
];

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
  follower: {
    id: string;
    status: 'online' | 'offline' | 'warning' | 'error';
    pnl: string;
    positions: number;
    lastActive: string;
  };
}

const FollowerItem: React.FC<FollowerItemProps> = ({ follower }) => {
  const theme = useTheme();
  
  const getPnlColor = () => {
    if (follower.pnl.startsWith('+')) return theme.palette.trading.profit;
    if (follower.pnl.startsWith('-')) return theme.palette.trading.loss;
    return theme.palette.trading.neutral;
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
            <StatusIndicator status={follower.status} />
            <Typography variant="subtitle2" fontWeight="medium">
              {follower.id}
            </Typography>
          </Box>
          <Typography 
            variant="subtitle2" 
            fontWeight="medium"
            sx={{ color: getPnlColor() }}
          >
            {follower.pnl}
          </Typography>
        </Box>
        
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="caption" color="text.secondary">
            Positions: {follower.positions}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Last active: {follower.lastActive}
          </Typography>
        </Box>
      </Box>
    </ListItem>
  );
};

interface ActiveFollowersListProps {
  title?: string;
  onViewAll?: () => void;
}

const ActiveFollowersList: React.FC<ActiveFollowersListProps> = ({ 
  title = 'ACTIVE FOLLOWERS',
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
          {mockFollowers.map((follower) => (
            <FollowerItem key={follower.id} follower={follower} />
          ))}
        </List>
      </CardContent>
    </Card>
  );
};

export default ActiveFollowersList;