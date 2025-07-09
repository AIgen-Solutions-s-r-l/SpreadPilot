import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Typography,
  Button,
  Box,
  Paper,
  TextField,
  InputAdornment,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Collapse,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Select,
  FormControl,
  InputLabel,
  useTheme,
  alpha,
  Tooltip as MuiTooltip,
  CircularProgress,
  Alert,
} from '@mui/material';
import Grid2 from '@mui/material/Grid';
import { DataGrid, GridColDef, GridRenderCellParams, GridActionsCellItem } from '@mui/x-data-grid';
import {
  Add as AddIcon,
  Search as SearchIcon,
  SortByAlpha as SortByAlphaIcon,
  GetApp as GetAppIcon,
  Tune as TuneIcon,
  CheckCircleOutline as CheckCircleOutlineIcon,
  HighlightOff as HighlightOffIcon,
  WarningAmberOutlined as WarningAmberOutlinedIcon,
  ErrorOutline as ErrorOutlineIcon,
  Edit as EditIcon,
  MoreVert as MoreVertIcon,
  Visibility as VisibilityIcon,
  Article as ArticleIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Close as CloseIcon,
  FiberManualRecord as FiberManualRecordIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { LineChart, Line, YAxis, ResponsiveContainer } from 'recharts';
import { TimeValueBadge } from '../components/common/TimeValueBadge';

// Import services
import { getFollowers, enableFollower, disableFollower, closeFollowerPosition } from '../services/followerService';
import { getPnlToday, getPnlMonth } from '../services/pnlService';
import { getHealth, getTimeValue, restartService, getHealthColor, getTimeValueBadgeColor } from '../services/healthService';
import type { Follower } from '../schemas/follower.schema';
import type { FollowerPnlArray } from '../schemas/pnl.schema';
import type { HealthResponse, TimeValue } from '../services/healthService';

// Extended Follower type with additional UI data
interface FollowerWithUI extends Follower {
  botStatus: 'ONLINE' | 'OFFLINE' | 'WARN' | 'ERROR';
  ibgwStatus: 'CONN' | 'DISC' | 'WARN' | 'ERROR';
  pnlToday: number;
  pnlMonth: number;
  timeValue?: TimeValue;
}

const getStatusChipProps = (status: string, theme: any) => {
  switch (status) {
    case 'ACTIVE':
    case 'ONLINE':
    case 'CONN':
      return {
        label: status,
        color: 'success' as const,
        icon: <CheckCircleOutlineIcon />,
        sx: { backgroundColor: alpha(theme.palette.success.main, 0.1), color: 'success.dark', fontWeight:'medium' }
      };
    case 'INACTIVE':
    case 'OFFLINE':
    case 'DISC':
      return {
        label: status,
        color: 'default' as const,
        icon: <HighlightOffIcon />,
        sx: { backgroundColor: alpha(theme.palette.grey[500], 0.1), color: 'text.secondary', fontWeight:'medium' }
      };
    case 'WARN':
      return {
        label: status,
        color: 'warning' as const,
        icon: <WarningAmberOutlinedIcon />,
        sx: { backgroundColor: alpha(theme.palette.warning.main, 0.1), color: 'warning.dark', fontWeight:'medium' }
      };
    case 'ERROR':
      return {
        label: status,
        color: 'error' as const,
        icon: <ErrorOutlineIcon />,
        sx: { backgroundColor: alpha(theme.palette.error.main, 0.1), color: 'error.dark', fontWeight:'medium' }
      };
    default:
      return { label: status, color: 'default' as const, sx: {fontWeight:'medium'} };
  }
};


const ServiceHealthDot: React.FC<{ health?: HealthResponse }> = ({ health }) => {
  const theme = useTheme();
  
  if (!health) return null;
  
  const color = getHealthColor(health.overall_status);
  const colorMap = {
    green: theme.palette.success.main,
    yellow: theme.palette.warning.main,
    red: theme.palette.error.main,
    gray: theme.palette.grey[500],
  };
  
  return (
    <MuiTooltip title={`System Health: ${health.overall_status}`}>
      <FiberManualRecordIcon 
        sx={{ 
          color: colorMap[color as keyof typeof colorMap],
          fontSize: 16,
        }} 
      />
    </MuiTooltip>
  );
};

const FollowersPageV3: React.FC = () => {
  const theme = useTheme();
  const [followers, setFollowers] = useState<FollowerWithUI[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(5);
  const [openAddDialog, setOpenAddDialog] = useState(false);
  const [openConfirmDialog, setOpenConfirmDialog] = useState(false);
  const [actionFollower, setActionFollower] = useState<FollowerWithUI | null>(null);
  const [actionType, setActionType] = useState<string | null>(null);
  const [pin, setPin] = useState('');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const [serviceMenuAnchor, setServiceMenuAnchor] = useState<null | HTMLElement>(null);
  const openActionMenu = Boolean(anchorEl);
  const openServiceMenu = Boolean(serviceMenuAnchor);

  // Polling interval for health check
  useEffect(() => {
    const interval = setInterval(() => {
      fetchHealth();
    }, 15000); // Poll every 15 seconds
    
    return () => clearInterval(interval);
  }, []);

  const fetchHealth = async () => {
    try {
      const healthData = await getHealth();
      setHealth(healthData);
    } catch (err) {
      console.error('Failed to fetch health:', err);
    }
  };

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch followers
      const followersData = await getFollowers();
      
      // Fetch today's P&L
      const todayPnl = await getPnlToday();
      const monthPnl = await getPnlMonth();
      
      // Fetch time values for each follower
      const timeValuePromises = followersData.map(f => 
        getTimeValue(f.id).catch(() => null)
      );
      const timeValues = await Promise.all(timeValuePromises);
      
      // Combine data
      const enrichedFollowers: FollowerWithUI[] = followersData.map((follower, index) => {
        const todayPnlData = todayPnl.find(p => p.follower_id === follower.id);
        const monthPnlData = monthPnl.find(p => p.follower_id === follower.id);
        
        return {
          ...follower,
          botStatus: follower.enabled ? 'ONLINE' : 'OFFLINE',
          ibgwStatus: follower.enabled ? 'CONN' : 'DISC',
          pnlToday: todayPnlData?.pnl || 0,
          pnlMonth: monthPnlData?.pnl || 0,
          timeValue: timeValues[index] || undefined,
        };
      });
      
      setFollowers(enrichedFollowers);
      
      // Fetch initial health status
      await fetchHealth();
      
    } catch (err) {
      console.error('Failed to fetch data:', err);
      setError('Failed to load followers data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleActionMenuClick = (event: React.MouseEvent<HTMLElement>, follower: FollowerWithUI) => {
    setAnchorEl(event.currentTarget);
    setActionFollower(follower);
  };

  const handleActionMenuClose = () => {
    setAnchorEl(null);
    setActionFollower(null);
  };

  const handleServiceMenuClick = (event: React.MouseEvent<HTMLElement>) => {
    setServiceMenuAnchor(event.currentTarget);
  };

  const handleServiceMenuClose = () => {
    setServiceMenuAnchor(null);
  };

  const handleRestartService = async (serviceName: string) => {
    try {
      await restartService(serviceName);
      handleServiceMenuClose();
      // Refresh health status
      await fetchHealth();
    } catch (err) {
      console.error('Failed to restart service:', err);
    }
  };

  const handleRowClick = (id: string) => {
    setExpandedRow(expandedRow === id ? null : id);
  };
  
  const handleOpenAddDialog = () => setOpenAddDialog(true);
  const handleCloseAddDialog = () => setOpenAddDialog(false);

  const handleConfirmAction = (follower: FollowerWithUI, type: string) => {
    setActionFollower(follower);
    setActionType(type);
    setPin('');
    setOpenConfirmDialog(true);
    handleActionMenuClose();
  };

  const handleCloseConfirmDialog = () => {
    setOpenConfirmDialog(false);
    setActionFollower(null);
    setActionType(null);
    setPin('');
  };

  const executeConfirmedAction = async () => {
    if (!actionFollower || !actionType) return;
    
    try {
      switch (actionType) {
        case 'DISABLE':
          await disableFollower(actionFollower.id);
          break;
        case 'ENABLE':
          await enableFollower(actionFollower.id);
          break;
        case 'CLOSE_POSITIONS':
          if (!pin) {
            alert('PIN is required');
            return;
          }
          await closeFollowerPosition(actionFollower.id, pin);
          break;
      }
      
      // Refresh data
      await fetchData();
      handleCloseConfirmDialog();
    } catch (err: any) {
      alert(err.message || 'Action failed');
    }
  };

  const formatCurrency = (value: number): string => {
    const prefix = value >= 0 ? '+' : '';
    return `${prefix}$${Math.abs(value).toFixed(2)}`;
  };

  const columns: GridColDef<FollowerWithUI>[] = [
    {
      field: 'id',
      headerName: 'ID',
      flex: 1,
      minWidth: 150,
      renderCell: (params: GridRenderCellParams<any, FollowerWithUI>) => (
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <IconButton size="small" onClick={() => handleRowClick(params.row.id)} sx={{ mr: 1 }}>
            {expandedRow === params.row.id ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
          <Typography variant="body2" fontWeight="medium">{params.row.id}</Typography>
        </Box>
      )
    },
    {
      field: 'enabled',
      headerName: 'Status',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams<any, boolean>) => {
        const status = params.value ? 'ACTIVE' : 'INACTIVE';
        const chipProps = getStatusChipProps(status, theme);
        return <Chip {...chipProps} size="small" />;
      },
    },
    {
      field: 'timeValue',
      headerName: 'Time Value',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams<any, TimeValue>) => (
        <TimeValueBadge timeValue={params.value?.time_value} />
      ),
    },
    {
      field: 'positions',
      headerName: 'Positions',
      flex: 1.2,
      minWidth: 150,
      renderCell: (params: GridRenderCellParams<any, FollowerWithUI>) => (
        <Box>
          <Typography variant="body2" component="span" fontWeight="medium">
            {params.row.active_positions || 0}
          </Typography>
        </Box>
      )
    },
    {
      field: 'pnlToday',
      headerName: 'P&L Today',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams<any, number>) => (
        <Typography 
          variant="body2" 
          fontWeight="medium" 
          sx={{ 
            color: params.value < 0 ? theme.palette.error.main : theme.palette.success.main 
          }}
        >
          {formatCurrency(params.value)}
        </Typography>
      ),
    },
    {
      field: 'pnlMonth',
      headerName: 'P&L Month',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams<any, number>) => (
        <Typography 
          variant="body2" 
          fontWeight="medium" 
          sx={{ 
            color: params.value < 0 ? theme.palette.error.main : theme.palette.success.main 
          }}
        >
          {formatCurrency(params.value)}
        </Typography>
      ),
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 100,
      cellClassName: 'actions',
      getActions: ({ row }: { row: FollowerWithUI }) => [
        <GridActionsCellItem
          icon={<EditIcon />}
          label="Edit"
          onClick={() => { handleOpenAddDialog(); }}
          color="primary"
        />,
        <GridActionsCellItem
          icon={<MoreVertIcon />}
          label="More"
          onClick={(event) => handleActionMenuClick(event, row)}
        />,
      ],
    },
  ];

  if (loading) {
    return (
      <Container maxWidth="xl" sx={{ py: 3, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
              Followers Management
            </Typography>
            <ServiceHealthDot health={health} />
            <IconButton size="small" onClick={handleServiceMenuClick}>
              <RefreshIcon />
            </IconButton>
          </Box>
          <Typography variant="subtitle1" color="text.secondary">
            Manage and monitor all trading followers
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={handleOpenAddDialog}>
          Add New Follower
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid2 container spacing={2} alignItems="center">
          <Grid2 size={{xs: 12, sm: 6, md: 4}}>
            <TextField
              fullWidth
              variant="outlined"
              size="small"
              placeholder="Search followers by ID or account..."
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
          </Grid2>
          <Grid2 size={{xs: 6, sm: 3, md: 2}}>
            <FormControl fullWidth size="small">
              <InputLabel>Status</InputLabel>
              <Select defaultValue="ALL" label="Status">
                <MenuItem value="ALL">All</MenuItem>
                <MenuItem value="ACTIVE">Active</MenuItem>
                <MenuItem value="INACTIVE">Inactive</MenuItem>
              </Select>
            </FormControl>
          </Grid2>
          <Grid2 size={{xs: 6, sm: 3, md: 2}}>
            <FormControl fullWidth size="small">
              <InputLabel>Time Value</InputLabel>
              <Select defaultValue="ALL" label="Time Value">
                <MenuItem value="ALL">All</MenuItem>
                <MenuItem value="SAFE">Safe</MenuItem>
                <MenuItem value="RISK">Risk</MenuItem>
                <MenuItem value="CRITICAL">Critical</MenuItem>
              </Select>
            </FormControl>
          </Grid2>
          <Grid2 size={{xs: 12, sm: 12, md: 4}} sx={{display: 'flex', justifyContent: {xs: 'flex-start', md: 'flex-end'}, gap: 1, flexWrap: 'wrap'}}>
            <Button variant="outlined" size="small" startIcon={<SortByAlphaIcon />}>Sort</Button>
            <Button variant="outlined" size="small" startIcon={<GetAppIcon />}>Export</Button>
            <MuiTooltip title="Advanced Filters">
              <IconButton size="small"><TuneIcon /></IconButton>
            </MuiTooltip>
          </Grid2>
        </Grid2>
      </Paper>

      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        <DataGrid
          rows={followers}
          columns={columns}
          autoHeight
          pageSizeOptions={[5, 10, 25]}
          initialState={{
            pagination: {
              paginationModel: { pageSize: rowsPerPage, page: page },
            },
          }}
          paginationModel={{ pageSize: rowsPerPage, page: page }}
          onPaginationModelChange={(model) => {
            setPage(model.page);
            setRowsPerPage(model.pageSize);
          }}
          density="compact"
          slots={{
            noRowsOverlay: () => <Box sx={{p:3, textAlign: 'center'}}>No followers found.</Box>,
          }}
          sx={{
            '& .MuiDataGrid-columnHeaders': {
              backgroundColor: alpha(theme.palette.primary.light, 0.1),
            },
            '& .MuiDataGrid-row': {
              '&:hover': {
                backgroundColor: alpha(theme.palette.primary.main, 0.05)
              }
            }
          }}
          getRowId={(row) => row.id}
        />
      </Paper>

      {expandedRow && followers.find(f => f.id === expandedRow) && (
        <Collapse in={!!expandedRow} timeout="auto" unmountOnExit sx={{mt: 1}}>
          <ExpandedFollowerDetail follower={followers.find(f => f.id === expandedRow)!} />
        </Collapse>
      )}
      
      {/* Action Menu */}
      {actionFollower && (
        <Menu
          anchorEl={anchorEl}
          open={openActionMenu}
          onClose={handleActionMenuClose}
        >
          <MenuItem onClick={() => { console.log("View Trades", actionFollower.id); handleActionMenuClose(); }}>
            <ListItemIcon><VisibilityIcon fontSize="small" /></ListItemIcon>
            <ListItemText>View Trades</ListItemText>
          </MenuItem>
          <MenuItem onClick={() => { console.log("View Logs", actionFollower.id); handleActionMenuClose(); }}>
            <ListItemIcon><ArticleIcon fontSize="small" /></ListItemIcon>
            <ListItemText>View Logs</ListItemText>
          </MenuItem>
          <MenuItem 
            onClick={() => handleConfirmAction(actionFollower, actionFollower.enabled ? 'DISABLE' : 'ENABLE')} 
            sx={{color: actionFollower.enabled ? 'warning.main' : 'success.main'}}
          >
            <ListItemIcon>
              {actionFollower.enabled ? 
                <HighlightOffIcon fontSize="small" color="warning" /> : 
                <CheckCircleOutlineIcon fontSize="small" color="success" />
              }
            </ListItemIcon>
            <ListItemText>{actionFollower.enabled ? 'Disable' : 'Enable'}</ListItemText>
          </MenuItem>
          <MenuItem onClick={() => handleConfirmAction(actionFollower, 'CLOSE_POSITIONS')} sx={{color: 'error.main'}}>
            <ListItemIcon><CloseIcon fontSize="small" color="error" /></ListItemIcon>
            <ListItemText>Close Positions</ListItemText>
          </MenuItem>
        </Menu>
      )}

      {/* Service Menu */}
      <Menu
        anchorEl={serviceMenuAnchor}
        open={openServiceMenu}
        onClose={handleServiceMenuClose}
      >
        {health?.services.map((service) => (
          <MenuItem 
            key={service.name}
            onClick={() => handleRestartService(service.name)}
          >
            <ListItemIcon>
              <FiberManualRecordIcon 
                sx={{ 
                  color: service.status === 'healthy' ? 
                    theme.palette.success.main : 
                    theme.palette.error.main,
                  fontSize: 12,
                }} 
              />
            </ListItemIcon>
            <ListItemText>
              Restart {service.name}
            </ListItemText>
          </MenuItem>
        ))}
      </Menu>

      {/* Add Dialog */}
      <Dialog open={openAddDialog} onClose={handleCloseAddDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Add New Follower</DialogTitle>
        <DialogContent>
          <TextField margin="dense" label="Follower ID" type="text" fullWidth variant="outlined" />
          <TextField margin="dense" label="Email" type="email" fullWidth variant="outlined" />
          <TextField margin="dense" label="IBAN" type="text" fullWidth variant="outlined" />
          <TextField margin="dense" label="Commission %" type="number" fullWidth variant="outlined" />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseAddDialog}>Cancel</Button>
          <Button onClick={handleCloseAddDialog} variant="contained">Save Follower</Button>
        </DialogActions>
      </Dialog>

      {/* Confirm Dialog */}
      <Dialog open={openConfirmDialog} onClose={handleCloseConfirmDialog}>
        <DialogTitle sx={{display: 'flex', alignItems: 'center'}}>
          <WarningAmberOutlinedIcon color="warning" sx={{mr:1}}/> Confirm Action
        </DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to {actionType?.toLowerCase().replace('_', ' ')} for follower {actionFollower?.id}?
            {actionType === 'CLOSE_POSITIONS' && " This action cannot be undone."}
          </Typography>
          {actionType === 'CLOSE_POSITIONS' && (
            <TextField 
              margin="dense" 
              label="PIN" 
              type="password" 
              fullWidth 
              variant="outlined" 
              sx={{mt:2}}
              value={pin}
              onChange={(e) => setPin(e.target.value)}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseConfirmDialog}>Cancel</Button>
          <Button 
            onClick={executeConfirmedAction} 
            variant="contained" 
            color={actionType === 'CLOSE_POSITIONS' ? "error" : "primary"}
          >
            Confirm {actionType?.toLowerCase().replace('_', ' ')}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default FollowersPageV3;

const ExpandedFollowerDetail: React.FC<{ follower: FollowerWithUI }> = ({ follower }) => {
  const theme = useTheme();
  
  return (
    <Box sx={{ p: 2, bgcolor: alpha(theme.palette.primary.light, 0.05), borderTop: `1px solid ${theme.palette.divider}` }}>
      <Grid2 container spacing={2}>
        <Grid2 size={{xs: 12, md: 4}}>
          <Typography variant="subtitle2" gutterBottom color="text.secondary">ACCOUNT DETAILS</Typography>
          <Paper variant="outlined" sx={{p:2}}>
            <Typography variant="body2"><strong>Follower ID:</strong> {follower.id}</Typography>
            <Typography variant="body2"><strong>Email:</strong> {follower.email || 'N/A'}</Typography>
            <Typography variant="body2"><strong>IBAN:</strong> {follower.iban || 'N/A'}</Typography>
            <Typography variant="body2"><strong>Commission:</strong> {follower.commission_pct}%</Typography>
          </Paper>
        </Grid2>
        <Grid2 size={{xs: 12, md: 4}}>
          <Typography variant="subtitle2" gutterBottom color="text.secondary">TIME VALUE</Typography>
          <Paper variant="outlined" sx={{p:2}}>
            {follower.timeValue ? (
              <>
                <Typography variant="body2">
                  <strong>Total Time Value:</strong> ${follower.timeValue.time_value.toFixed(2)}
                </Typography>
                <Typography variant="body2">
                  <strong>Status:</strong> <TimeValueBadge timeValue={follower.timeValue?.time_value} />
                </Typography>
                {follower.timeValue.positions?.map((pos, idx) => (
                  <Typography key={idx} variant="caption" display="block">
                    {pos.symbol} ({pos.expiration}): ${pos.time_value.toFixed(2)}
                  </Typography>
                ))}
              </>
            ) : (
              <Typography variant="body2">No time value data available</Typography>
            )}
          </Paper>
        </Grid2>
        <Grid2 size={{xs: 12, md: 4}}>
          <Typography variant="subtitle2" gutterBottom color="text.secondary">PERFORMANCE</Typography>
          <Paper variant="outlined" sx={{p:2}}>
            <Typography variant="body2">
              <strong>P&L Today:</strong>
              <Typography 
                component="span" 
                sx={{ 
                  color: follower.pnlToday < 0 ? theme.palette.error.main : theme.palette.success.main, 
                  fontWeight: 'medium' 
                }}
              > 
                {formatCurrency(follower.pnlToday)}
              </Typography>
            </Typography>
            <Typography variant="body2">
              <strong>P&L Month:</strong>
              <Typography 
                component="span" 
                sx={{ 
                  color: follower.pnlMonth < 0 ? theme.palette.error.main : theme.palette.success.main, 
                  fontWeight: 'medium' 
                }}
              > 
                {formatCurrency(follower.pnlMonth)}
              </Typography>
            </Typography>
          </Paper>
        </Grid2>
      </Grid2>
    </Box>
  );
};

// Utility function
const formatCurrency = (value: number): string => {
  const prefix = value >= 0 ? '+' : '';
  return `${prefix}$${Math.abs(value).toFixed(2)}`;
};