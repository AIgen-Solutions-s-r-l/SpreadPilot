import React, { useState } from 'react';
import { 
  Alert,
  AlertTitle,
  Box,
  Typography,
  IconButton,
  Collapse,
  useMediaQuery,
  useTheme,
  Stack
} from '@mui/material';
import {
  CheckCircleOutline as CheckCircleIcon,
  ExpandMore as ExpandMoreIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';

interface StatusItemProps {
  label: string;
  status: 'online' | 'offline' | 'warning' | 'error';
}

const StatusIndicator: React.FC<{ status: 'online' | 'offline' | 'warning' | 'error' }> = ({ status }) => {
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
        width: 10,
        height: 10,
        borderRadius: '50%',
        bgcolor: getStatusColor(),
        mr: 1,
        // boxShadow: '0 0 0 2px #fff', // Removed boxShadow
      }}
    />
  );
};

const StatusItem: React.FC<StatusItemProps> = ({ label, status }) => {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', py: 0.5 }}>
      <StatusIndicator status={status} />
      <Typography variant="body2" color="inherit">
        {label}
      </Typography>
    </Box>
  );
};

interface SystemStatusBannerProps {
  onRefresh?: () => void;
  isConnected?: boolean;
  activeFollowerCount?: number;
  totalFollowerCount?: number;
}

const SystemStatusBanner: React.FC<SystemStatusBannerProps> = ({ 
  onRefresh, 
  isConnected = false, 
  activeFollowerCount = 0, 
  totalFollowerCount = 0 
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  const isSystemHealthy = isConnected && activeFollowerCount > 0;
  
  const handleRefresh = () => {
    if (onRefresh) {
      onRefresh();
    }
  };
  
  return (
    <Alert
      severity={isSystemHealthy ? "success" : "warning"}
      iconMapping={{
        success: <CheckCircleIcon fontSize="inherit" />,
      }}
      action={
        <>
          <IconButton
            color="inherit"
            size="small"
            onClick={() => setIsExpanded(!isExpanded)}
            aria-expanded={isExpanded}
            aria-label="show more"
            sx={{
              transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: theme.transitions.create('transform', {
                duration: theme.transitions.duration.shortest,
              }),
            }}
          >
            <ExpandMoreIcon />
          </IconButton>
          <IconButton color="inherit" size="small" onClick={handleRefresh} aria-label="refresh status">
            <RefreshIcon />
          </IconButton>
        </>
      }
      sx={{
        mb: 3,
        borderRadius: 2,
        '& .MuiAlert-icon': {
          fontSize: 28, // Make icon larger
        },
        '& .MuiAlert-message': {
          width: '100%' // Ensure message area takes full width
        }
      }}
    >
      <AlertTitle sx={{ fontWeight: 600, letterSpacing: 0.5, fontSize: '1.1rem' }}>
        SYSTEM STATUS: {isSystemHealthy ? 'OPERATIONAL' : 'LIMITED'}
      </AlertTitle>
      <Collapse in={isExpanded || !isMobile} sx={{ width: '100%' }}>
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={{ xs: 0.5, sm: 2 }}
          mt={1}
          flexWrap="wrap"
        >
          <StatusItem label="Trading Bot: Online" status="online" />
          <StatusItem label={`WebSocket: ${isConnected ? 'Connected' : 'Disconnected'}`} status={isConnected ? 'online' : 'error'} />
          <StatusItem label={`Followers: ${activeFollowerCount}/${totalFollowerCount} Active`} status={activeFollowerCount > 0 ? 'online' : 'warning'} />
          <StatusItem label={`Last Update: ${new Date().toLocaleTimeString()}`} status="online" />
        </Stack>
      </Collapse>
    </Alert>
  );
};

export default SystemStatusBanner;