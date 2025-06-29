import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  CircularProgress,
  Alert,
  Tooltip,
  Collapse,
  useTheme,
  alpha,
} from '@mui/material';
import {
  HealthAndSafety as HealthIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  RestartAlt as RestartIcon,
  Storage as DatabaseIcon,
  Memory as SystemIcon,
} from '@mui/icons-material';
import { useServiceHealth, getHealthColor, ServiceHealth } from '../../hooks/useServiceHealth';

interface ServiceHealthWidgetProps {
  title?: string;
  compact?: boolean;
}

const ServiceHealthWidget: React.FC<ServiceHealthWidgetProps> = ({ 
  title = 'SERVICE HEALTH',
  compact = false 
}) => {
  const theme = useTheme();
  const { health, loading, error, refresh, restartService, isRestarting } = useServiceHealth();
  const [expanded, setExpanded] = useState(!compact);
  const [restartDialogOpen, setRestartDialogOpen] = useState(false);
  const [selectedService, setSelectedService] = useState<ServiceHealth | null>(null);

  const handleRestartClick = (service: ServiceHealth) => {
    setSelectedService(service);
    setRestartDialogOpen(true);
  };

  const handleRestartConfirm = async () => {
    if (selectedService) {
      try {
        await restartService(selectedService.name);
        setRestartDialogOpen(false);
        setSelectedService(null);
      } catch (error) {
        // Error is handled in the hook
      }
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon sx={{ color: theme.palette.success.main }} />;
      case 'unhealthy':
        return <ErrorIcon sx={{ color: theme.palette.error.main }} />;
      case 'unreachable':
        return <WarningIcon sx={{ color: theme.palette.warning.main }} />;
      default:
        return <ErrorIcon sx={{ color: theme.palette.grey[500] }} />;
    }
  };

  const getOverallHealthDot = () => {
    const color = getHealthColor(health?.overall_status);
    return (
      <Box
        sx={{
          width: 12,
          height: 12,
          borderRadius: '50%',
          backgroundColor: color,
          boxShadow: `0 0 0 2px ${alpha(color, 0.3)}`,
          animation: health?.overall_status === 'RED' ? 'pulse 2s infinite' : 'none',
          '@keyframes pulse': {
            '0%': { boxShadow: `0 0 0 2px ${alpha(color, 0.3)}` },
            '50%': { boxShadow: `0 0 0 6px ${alpha(color, 0.1)}` },
            '100%': { boxShadow: `0 0 0 2px ${alpha(color, 0.3)}` },
          },
        }}
      />
    );
  };

  if (loading && !health) {
    return (
      <Card sx={{ height: '100%' }}>
        <CardContent sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
          <CircularProgress />
        </CardContent>
      </Card>
    );
  }

  if (error && !health) {
    return (
      <Card sx={{ height: '100%' }}>
        <CardContent>
          <Alert severity="error" action={
            <Button color="inherit" size="small" onClick={refresh}>
              Retry
            </Button>
          }>
            {error}
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card sx={{ 
      height: '100%',
      transition: 'transform 0.3s, box-shadow 0.3s',
      '&:hover': {
        transform: 'translateY(-4px)',
        boxShadow: theme.shadows[4],
      }
    }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <HealthIcon color="primary" />
            <Typography variant="h6" component="h3" fontWeight="medium">
              {title}
            </Typography>
            <Box ml={1}>{getOverallHealthDot()}</Box>
            <Chip 
              label={health?.overall_status || 'UNKNOWN'} 
              size="small"
              sx={{
                ml: 1,
                backgroundColor: alpha(getHealthColor(health?.overall_status), 0.1),
                color: getHealthColor(health?.overall_status),
                fontWeight: 'medium',
              }}
            />
          </Box>
          <Box display="flex" gap={1}>
            <Tooltip title="Refresh">
              <IconButton size="small" onClick={refresh} disabled={loading}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            {compact && (
              <IconButton size="small" onClick={() => setExpanded(!expanded)}>
                {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            )}
          </Box>
        </Box>

        <Collapse in={expanded}>
          {/* System Health */}
          <Box mb={2}>
            <Box display="flex" alignItems="center" gap={1} mb={1}>
              <SystemIcon fontSize="small" color="action" />
              <Typography variant="subtitle2" color="text.secondary">
                System Resources
              </Typography>
            </Box>
            <Box display="flex" gap={2} flexWrap="wrap">
              <Chip
                label={`CPU: ${health?.system.cpu_percent.toFixed(1)}%`}
                size="small"
                color={health?.system.cpu_percent! > 80 ? 'error' : 'default'}
                variant={health?.system.cpu_percent! > 80 ? 'filled' : 'outlined'}
              />
              <Chip
                label={`Memory: ${health?.system.memory_percent.toFixed(1)}%`}
                size="small"
                color={health?.system.memory_percent! > 80 ? 'error' : 'default'}
                variant={health?.system.memory_percent! > 80 ? 'filled' : 'outlined'}
              />
              <Chip
                label={`Disk: ${health?.system.disk_percent.toFixed(1)}%`}
                size="small"
                color={health?.system.disk_percent! > 90 ? 'error' : 'default'}
                variant={health?.system.disk_percent! > 90 ? 'filled' : 'outlined'}
              />
            </Box>
          </Box>

          {/* Database Status */}
          <Box mb={2}>
            <Box display="flex" alignItems="center" gap={1} mb={1}>
              <DatabaseIcon fontSize="small" color="action" />
              <Typography variant="subtitle2" color="text.secondary">
                Database
              </Typography>
            </Box>
            <Chip
              icon={health?.database.status === 'healthy' ? <CheckCircleIcon /> : <ErrorIcon />}
              label={`MongoDB: ${health?.database.status}`}
              size="small"
              color={health?.database.status === 'healthy' ? 'success' : 'error'}
              variant="outlined"
            />
          </Box>

          {/* Services */}
          <Box>
            <Typography variant="subtitle2" color="text.secondary" mb={1}>
              Services
            </Typography>
            <List dense disablePadding>
              {health?.services.map((service) => (
                <ListItem
                  key={service.name}
                  sx={{
                    py: 1,
                    px: 2,
                    mb: 0.5,
                    borderRadius: 1,
                    backgroundColor: alpha(theme.palette.action.hover, 0.04),
                    '&:hover': {
                      backgroundColor: alpha(theme.palette.action.hover, 0.08),
                    },
                  }}
                >
                  <Box display="flex" alignItems="center" gap={1} width="100%">
                    {getStatusIcon(service.status)}
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="body2" fontWeight="medium">
                            {service.name}
                          </Typography>
                          {service.critical && (
                            <Chip label="Critical" size="small" color="error" sx={{ height: 18 }} />
                          )}
                        </Box>
                      }
                      secondary={
                        <Typography variant="caption" color="text.secondary">
                          {service.status === 'healthy' && service.response_time_ms
                            ? `Response time: ${service.response_time_ms.toFixed(0)}ms`
                            : service.error || service.status}
                        </Typography>
                      }
                    />
                    <ListItemSecondaryAction>
                      <Tooltip title="Restart Service">
                        <span>
                          <IconButton
                            edge="end"
                            size="small"
                            onClick={() => handleRestartClick(service)}
                            disabled={isRestarting || service.status === 'healthy'}
                          >
                            <RestartIcon />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </ListItemSecondaryAction>
                  </Box>
                </ListItem>
              ))}
            </List>
          </Box>
        </Collapse>
      </CardContent>

      {/* Restart Confirmation Dialog */}
      <Dialog open={restartDialogOpen} onClose={() => setRestartDialogOpen(false)}>
        <DialogTitle>Confirm Service Restart</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to restart the <strong>{selectedService?.name}</strong> service?
            {selectedService?.critical && (
              <Alert severity="warning" sx={{ mt: 2 }}>
                This is a critical service. Restarting it may temporarily affect system operations.
              </Alert>
            )}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRestartDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleRestartConfirm}
            variant="contained"
            color="warning"
            disabled={isRestarting}
            startIcon={isRestarting ? <CircularProgress size={16} /> : <RestartIcon />}
          >
            {isRestarting ? 'Restarting...' : 'Restart Service'}
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
};

export default ServiceHealthWidget;