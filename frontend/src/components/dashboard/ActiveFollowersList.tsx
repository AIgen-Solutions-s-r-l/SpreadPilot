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
  CircularProgress
} from '@mui/material';
import { 
  People as PeopleIcon,
  ArrowForward as ArrowForwardIcon
} from '@mui/icons-material';
import { useFollowers } from '../../hooks/useFollowers';
import { Follower } from '../../schemas/follower.schema';

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
  
  // Logic to determine PnL (assuming follower object might have pnl data in the future or we fetch it)
  // For now, we'll display a placeholder or 0 if not available
  const pnl = 0; // Placeholder until PnL is integrated into Follower model or fetched separately
  const pnlString = pnl >= 0 ? `+$${pnl.toFixed(2)}` : `-$${Math.abs(pnl).toFixed(2)}`;

  const getPnlColor = () => {
    if (pnl > 0) return theme.palette.trading.profit;
    if (pnl < 0) return theme.palette.trading.loss;
    return theme.palette.trading.neutral;
  };

  // Determine status based on enabled/active flags
  const status = follower.enabled && follower.botStatus === 'RUNNING' ? 'online' : 'offline';
  
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
            <StatusIndicator status={status} />
            <Typography variant="subtitle2" fontWeight="medium">
              {follower.id}
            </Typography>
          </Box>
          <Typography 
            variant="subtitle2" 
            fontWeight="medium"
            sx={{ color: getPnlColor() }}
          >
            {pnlString}
          </Typography>
        </Box>
        
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="caption" color="text.secondary">
            Positions: {follower.positions?.count || 0}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Bot Status: {follower.botStatus}
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
  const { followers, loading } = useFollowers();
  const activeFollowers = followers.filter(f => f.enabled).slice(0, 5); // Show top 5 active

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
        
        {loading ? (
          <Box display="flex" justifyContent="center" p={2}>
            <CircularProgress size={24} />
          </Box>
        ) : (
          <List disablePadding>
            {activeFollowers.map((follower) => (
              <FollowerItem key={follower.id} follower={follower} />
            ))}
            {activeFollowers.length === 0 && (
               <Typography variant="body2" color="text.secondary" align="center">
                 No active followers
               </Typography>
            )}
          </List>
        )}
      </CardContent>
    </Card>
  );
};

export default ActiveFollowersList;