import React, { useState, useEffect, useRef } from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  TextField,
  InputAdornment,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  useTheme,
  alpha,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  Switch,
  FormControlLabel,
} from '@mui/material';
import Grid2 from '@mui/material/Grid';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  GetApp as GetAppIcon,
  Clear as ClearIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  BugReport as BugReportIcon,
  ErrorOutline as CriticalIcon,
  Stream as StreamIcon,
} from '@mui/icons-material';

// Hooks and services  
import { useLogs, useLogStats } from '../hooks/useLogs';
import { useWebSocket } from '../contexts/WebSocketContext';
import { LogLevel } from '../schemas/log.schema';

// Helper function to get log level color and icon
const getLogLevelProps = (level: LogLevel, theme: any) => {
  switch (level) {
    case LogLevel.CRITICAL:
      return {
        color: theme.palette.error.dark,
        bgcolor: alpha(theme.palette.error.main, 0.1),
        icon: <CriticalIcon fontSize="small" />,
      };
    case LogLevel.ERROR:
      return {
        color: theme.palette.error.main,
        bgcolor: alpha(theme.palette.error.main, 0.1),
        icon: <ErrorIcon fontSize="small" />,
      };
    case LogLevel.WARNING:
      return {
        color: theme.palette.warning.main,
        bgcolor: alpha(theme.palette.warning.main, 0.1),
        icon: <WarningIcon fontSize="small" />,
      };
    case LogLevel.INFO:
      return {
        color: theme.palette.info.main,
        bgcolor: alpha(theme.palette.info.main, 0.1),
        icon: <InfoIcon fontSize="small" />,
      };
    case LogLevel.DEBUG:
      return {
        color: theme.palette.grey[600],
        bgcolor: alpha(theme.palette.grey[500], 0.1),
        icon: <BugReportIcon fontSize="small" />,
      };
    default:
      return {
        color: theme.palette.text.primary,
        bgcolor: theme.palette.background.paper,
        icon: null,
      };
  }
};

const LogsPageV2: React.FC = () => {
  const theme = useTheme();
  const { isConnected } = useWebSocket();
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [streaming, setStreaming] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [levelFilter, setLevelFilter] = useState<LogLevel | ''>('');
  const [serviceFilter, setServiceFilter] = useState('');

  const {
    logs,
    totalCount,
    loading,
    error,
    filters,
    refresh,
    setFilters,
  } = useLogs({
    limit: 200,
    level: levelFilter || undefined,
    service: serviceFilter || undefined,
    search: searchTerm || undefined,
    autoRefresh: false,
    streaming,
  });

  const { stats, loading: statsLoading } = useLogStats();

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const handleLevelFilterChange = (level: LogLevel | '') => {
    setLevelFilter(level);
    setFilters({ level: level || undefined });
  };

  const handleServiceFilterChange = (service: string) => {
    setServiceFilter(service);
    setFilters({ service: service || undefined });
  };

  const handleSearchChange = (search: string) => {
    setSearchTerm(search);
    // Debounce search
    const timeoutId = setTimeout(() => {
      setFilters({ search: search || undefined });
    }, 300);
    return () => clearTimeout(timeoutId);
  };

  const handleClearFilters = () => {
    setSearchTerm('');
    setLevelFilter('');
    setServiceFilter('');
    setFilters({ level: undefined, service: undefined, search: undefined });
  };

  const handleExport = () => {
    const logText = logs.map(log => 
      `${new Date(log.timestamp).toISOString()} [${log.level}] [${log.service}] ${log.message}`
    ).join('\n');
    
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs_${new Date().toISOString()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Extract unique services from logs
  const uniqueServices = Array.from(new Set(logs.map(log => log.service))).sort();

  if (loading && logs.length === 0) {
    return (
      <Container>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl">
      <Box mb={4}>
        <Typography variant="h4" fontWeight="bold" gutterBottom>
          Log Console
        </Typography>
        <Box display="flex" alignItems="center" gap={2}>
          <Typography variant="body1" color="text.secondary">
            Real-time system logs and diagnostics
          </Typography>
          <Chip
            icon={isConnected ? <StreamIcon /> : <ErrorIcon />}
            label={isConnected ? 'WebSocket Connected' : 'WebSocket Disconnected'}
            color={isConnected ? 'success' : 'error'}
            size="small"
          />
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
          <Button onClick={refresh} sx={{ ml: 2 }}>Retry</Button>
        </Alert>
      )}

      {/* Stats Summary */}
      {!statsLoading && (
        <Grid2 container spacing={2} mb={3}>
          <Grid2 size={{ xs: 6, sm: 4, md: 2.4 }}>
            <Paper sx={{ p: 2, ...getLogLevelProps(LogLevel.CRITICAL, theme) }}>
              <Box display="flex" alignItems="center" gap={1}>
                <CriticalIcon />
                <Box>
                  <Typography variant="h6">{stats.criticalCount}</Typography>
                  <Typography variant="caption">Critical</Typography>
                </Box>
              </Box>
            </Paper>
          </Grid2>
          <Grid2 size={{ xs: 6, sm: 4, md: 2.4 }}>
            <Paper sx={{ p: 2, ...getLogLevelProps(LogLevel.ERROR, theme) }}>
              <Box display="flex" alignItems="center" gap={1}>
                <ErrorIcon />
                <Box>
                  <Typography variant="h6">{stats.errorCount}</Typography>
                  <Typography variant="caption">Errors</Typography>
                </Box>
              </Box>
            </Paper>
          </Grid2>
          <Grid2 size={{ xs: 6, sm: 4, md: 2.4 }}>
            <Paper sx={{ p: 2, ...getLogLevelProps(LogLevel.WARNING, theme) }}>
              <Box display="flex" alignItems="center" gap={1}>
                <WarningIcon />
                <Box>
                  <Typography variant="h6">{stats.warningCount}</Typography>
                  <Typography variant="caption">Warnings</Typography>
                </Box>
              </Box>
            </Paper>
          </Grid2>
          <Grid2 size={{ xs: 6, sm: 4, md: 2.4 }}>
            <Paper sx={{ p: 2, ...getLogLevelProps(LogLevel.INFO, theme) }}>
              <Box display="flex" alignItems="center" gap={1}>
                <InfoIcon />
                <Box>
                  <Typography variant="h6">{stats.infoCount}</Typography>
                  <Typography variant="caption">Info</Typography>
                </Box>
              </Box>
            </Paper>
          </Grid2>
          <Grid2 size={{ xs: 6, sm: 4, md: 2.4 }}>
            <Paper sx={{ p: 2, ...getLogLevelProps(LogLevel.DEBUG, theme) }}>
              <Box display="flex" alignItems="center" gap={1}>
                <BugReportIcon />
                <Box>
                  <Typography variant="h6">{stats.debugCount}</Typography>
                  <Typography variant="caption">Debug</Typography>
                </Box>
              </Box>
            </Paper>
          </Grid2>
        </Grid2>
      )}

      {/* Filters Bar */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box display="flex" gap={2} alignItems="center" flexWrap="wrap">
          <TextField
            placeholder="Search logs..."
            size="small"
            value={searchTerm}
            onChange={(e) => handleSearchChange(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
            sx={{ minWidth: 250 }}
          />
          
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Level</InputLabel>
            <Select
              value={levelFilter}
              onChange={(e) => handleLevelFilterChange(e.target.value as LogLevel | '')}
              label="Level"
            >
              <MenuItem value="">All</MenuItem>
              {Object.values(LogLevel).map(level => (
                <MenuItem key={level} value={level}>
                  <Box display="flex" alignItems="center" gap={1}>
                    {getLogLevelProps(level, theme).icon}
                    {level}
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Service</InputLabel>
            <Select
              value={serviceFilter}
              onChange={(e) => handleServiceFilterChange(e.target.value)}
              label="Service"
            >
              <MenuItem value="">All Services</MenuItem>
              {uniqueServices.map(service => (
                <MenuItem key={service} value={service}>{service}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControlLabel
            control={
              <Switch
                checked={streaming}
                onChange={(e) => setStreaming(e.target.checked)}
                color="primary"
              />
            }
            label="Live Stream"
          />

          <FormControlLabel
            control={
              <Switch
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                color="primary"
              />
            }
            label="Auto Scroll"
          />

          <Box sx={{ flexGrow: 1 }} />

          <Tooltip title="Clear Filters">
            <IconButton onClick={handleClearFilters} size="small">
              <ClearIcon />
            </IconButton>
          </Tooltip>

          <Button
            startIcon={<RefreshIcon />}
            onClick={refresh}
            variant="outlined"
            size="small"
          >
            Refresh
          </Button>

          <Button
            startIcon={<GetAppIcon />}
            onClick={handleExport}
            variant="outlined"
            size="small"
          >
            Export
          </Button>
        </Box>
      </Paper>

      {/* Logs Display */}
      <Paper sx={{ height: '60vh', display: 'flex', flexDirection: 'column' }}>
        <Box
          ref={logsContainerRef}
          sx={{
            flex: 1,
            overflow: 'auto',
            p: 2,
            bgcolor: theme.palette.grey[900],
            fontFamily: 'monospace',
            fontSize: '0.875rem',
          }}
        >
          {logs.length === 0 ? (
            <Typography color="text.secondary" align="center" sx={{ mt: 4 }}>
              No logs found matching the current filters
            </Typography>
          ) : (
            logs.map(log => (
              <Box
                key={log.id}
                sx={{
                  mb: 0.5,
                  p: 1,
                  borderRadius: 1,
                  '&:hover': {
                    bgcolor: alpha(theme.palette.primary.main, 0.05),
                  },
                }}
              >
                <Box display="flex" alignItems="flex-start" gap={1}>
                  <Typography
                    component="span"
                    sx={{
                      color: theme.palette.grey[500],
                      fontSize: '0.75rem',
                      minWidth: 180,
                    }}
                  >
                    {new Date(log.timestamp).toLocaleString()}
                  </Typography>
                  
                  <Chip
                    label={log.level}
                    size="small"
                    icon={getLogLevelProps(log.level, theme).icon}
                    sx={{
                      ...getLogLevelProps(log.level, theme),
                      height: 20,
                      fontSize: '0.7rem',
                      minWidth: 80,
                    }}
                  />
                  
                  <Typography
                    component="span"
                    sx={{
                      color: theme.palette.info.main,
                      fontSize: '0.8rem',
                      minWidth: 100,
                    }}
                  >
                    [{log.service}]
                  </Typography>
                  
                  <Typography
                    component="span"
                    sx={{
                      color: theme.palette.grey[100],
                      wordBreak: 'break-word',
                      flex: 1,
                    }}
                  >
                    {log.message}
                  </Typography>
                </Box>
                
                {log.extra && (
                  <Box sx={{ ml: '320px', mt: 0.5 }}>
                    <Typography
                      component="pre"
                      sx={{
                        color: theme.palette.grey[400],
                        fontSize: '0.75rem',
                        bgcolor: alpha(theme.palette.grey[800], 0.5),
                        p: 1,
                        borderRadius: 1,
                        overflow: 'auto',
                      }}
                    >
                      {JSON.stringify(log.extra, null, 2)}
                    </Typography>
                  </Box>
                )}
              </Box>
            ))
          )}
        </Box>
        
        <Box
          sx={{
            p: 1,
            borderTop: 1,
            borderColor: 'divider',
            bgcolor: 'background.paper',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Typography variant="caption" color="text.secondary">
            Showing {logs.length} of {totalCount} logs
          </Typography>
          {streaming && (
            <Chip
              icon={<StreamIcon />}
              label="Live streaming enabled"
              color="primary"
              size="small"
            />
          )}
        </Box>
      </Paper>
    </Container>
  );
};

export default LogsPageV2;