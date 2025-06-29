import React, { useState, useEffect } from 'react';
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
  Refresh as RefreshIcon,
  RestartAlt as RestartIcon,
} from '@mui/icons-material';
import { LineChart, Line, YAxis, ResponsiveContainer } from 'recharts';
import { useFollowers } from '../hooks/useFollowers';
import { usePnl } from '../hooks/usePnl';
import { TimeValueBadge } from '../components/common/TimeValueBadge';
import * as followerService from '../services/followerService';
import apiClient from '../services/api';
import type { Follower } from '../schemas/follower.schema';


// Service status mapping
const mapBotStatus = (status: string): 'ONLINE' | 'OFFLINE' | 'WARN' | 'ERROR' => {
  switch (status) {
    case 'RUNNING': return 'ONLINE';
    case 'STOPPED': return 'OFFLINE';
    case 'STARTING': return 'WARN';
    case 'ERROR': return 'ERROR';
    default: return 'OFFLINE';
  }
};

const mapIbGwStatus = (status: string): 'CONN' | 'DISC' | 'WARN' | 'ERROR' => {
  switch (status) {
    case 'CONNECTED': return 'CONN';
    case 'DISCONNECTED': return 'DISC';
    case 'CONNECTING': return 'WARN';
    case 'ERROR': return 'ERROR';
    default: return 'DISC';
  }
};

const mapFollowerStatus = (enabled: boolean, botStatus: string): 'ACTIVE' | 'INACTIVE' | 'WARN' | 'ERROR' => {
  if (!enabled) return 'INACTIVE';
  if (botStatus === 'ERROR') return 'ERROR';
  if (botStatus === 'STARTING') return 'WARN';
  return 'ACTIVE';
};

type FollowerStatus = 'ACTIVE' | 'INACTIVE' | 'WARN' | 'ERROR';
type BotStatus = 'ONLINE' | 'OFFLINE' | 'WARN' | 'ERROR';
type IBGWStatus = 'CONN' | 'DISC' | 'WARN' | 'ERROR';

const getStatusChipProps = (status: FollowerStatus | BotStatus | IBGWStatus, theme: any) => {
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


const FollowersPage: React.FC = () => {
  const theme = useTheme();
  const { followers, loading, error, refresh } = useFollowers();
  const { todayPnl, monthlyPnl } = usePnl();
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(5);
  const [openAddDialog, setOpenAddDialog] = useState(false);
  const [openConfirmDialog, setOpenConfirmDialog] = useState(false);
  const [actionFollower, setActionFollower] = useState<any>(null);
  const [actionType, setActionType] = useState<string | null>(null);
  const [pinValue, setPinValue] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [restartDialogOpen, setRestartDialogOpen] = useState(false);
  const [restartService, setRestartService] = useState<string | null>(null);

  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const openActionMenu = Boolean(anchorEl);

  const handleActionMenuClick = (event: React.MouseEvent<HTMLElement>, follower: Follower) => {
    setAnchorEl(event.currentTarget);
    setActionFollower(follower);
  };
  const handleActionMenuClose = () => {
    setAnchorEl(null);
    setActionFollower(null);
  };

  const handleRowClick = (id: string) => {
    setExpandedRow(expandedRow === id ? null : id);
  };

  
  const handleOpenAddDialog = () => setOpenAddDialog(true);
  const handleCloseAddDialog = () => setOpenAddDialog(false);

  const handleConfirmAction = (follower: Follower, type: string) => {
    setActionFollower(follower);
    setActionType(type);
    setOpenConfirmDialog(true);
    handleActionMenuClose();
  };
  const handleCloseConfirmDialog = () => {
    setOpenConfirmDialog(false);
    setActionFollower(null);
    setActionType(null);
  };
  const executeConfirmedAction = async () => {
    if (!actionFollower || !actionType) return;

    setActionLoading(true);
    setActionError(null);

    try {
      switch (actionType) {
        case 'DISABLE':
          await followerService.disableFollower(actionFollower.id);
          await refresh();
          break;
        case 'CLOSE_POSITIONS':
          if (!pinValue || pinValue !== '0312') {
            setActionError('Invalid PIN');
            return;
          }
          await followerService.closeFollowerPosition(actionFollower.id, pinValue);
          break;
      }
      handleCloseConfirmDialog();
    } catch (error: any) {
      setActionError(error.message || 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleServiceRestart = async () => {
    if (!restartService) return;
    
    try {
      await apiClient.post(`/service/${restartService}/restart`);
      setRestartDialogOpen(false);
      setRestartService(null);
      // Refresh data after restart
      setTimeout(refresh, 3000);
    } catch (error) {
      console.error('Failed to restart service:', error);
    }
  };

  // Transform API data to display format
  const displayFollowers = followers.map(f => ({
    ...f,
    status: mapFollowerStatus(f.enabled, f.botStatus),
    botStatus: mapBotStatus(f.botStatus),
    ibgwStatus: mapIbGwStatus(f.ibGwStatus),
    pnlToday: f.pnlToday ? `${f.pnlToday >= 0 ? '+' : ''}$${f.pnlToday.toFixed(2)}` : '$0.00',
    pnlMtd: f.pnlMonth ? `${f.pnlMonth >= 0 ? '+' : ''}$${f.pnlMonth.toFixed(2)}` : '$0.00',
    positions: f.positions || { count: 0, value: 0 },
  }));



  const columns: GridColDef[] = [
    {
      field: 'id',
      headerName: 'ID',
      flex: 1,
      minWidth: 150,
      renderCell: (params: GridRenderCellParams) => (
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <IconButton size="small" onClick={() => handleRowClick(params.row.id)} sx={{ mr: 1 }}>
            {expandedRow === params.row.id ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
          <Typography variant="body2" fontWeight="medium">{params.row.id}</Typography>
        </Box>
      )
    },
    {
      field: 'status',
      headerName: 'Status',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams) => {
        if (params.value === undefined) return null;
        const chipProps = getStatusChipProps(params.value as FollowerStatus, theme);
        return <Chip {...chipProps} size="small" />;
      },
    },
    {
      field: 'botStatus',
      headerName: 'Bot',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams) => {
        if (params.value === undefined) return null;
        const chipProps = getStatusChipProps(params.value as BotStatus, theme);
        return (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip {...chipProps} size="small" />
            {params.value === 'ERROR' && (
              <IconButton 
                size="small" 
                onClick={(e) => {
                  e.stopPropagation();
                  setRestartService('trading-bot');
                  setRestartDialogOpen(true);
                }}
                sx={{ padding: 0.5 }}
              >
                <RestartIcon fontSize="small" />
              </IconButton>
            )}
          </Box>
        );
      },
    },
    {
      field: 'ibgwStatus',
      headerName: 'IBGW',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams) => {
        if (params.value === undefined) return null;
        const chipProps = getStatusChipProps(params.value as IBGWStatus, theme);
        return (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip {...chipProps} size="small" />
            {params.value === 'ERROR' && (
              <IconButton 
                size="small" 
                onClick={(e) => {
                  e.stopPropagation();
                  setRestartService('gateway');
                  setRestartDialogOpen(true);
                }}
                sx={{ padding: 0.5 }}
              >
                <RestartIcon fontSize="small" />
              </IconButton>
            )}
          </Box>
        );
      },
    },
    {
      field: 'positions',
      headerName: 'Positions',
      flex: 1.2,
      minWidth: 150,
      valueGetter: (value: any) => value ? `${value.count} ($${value.value.toFixed(0)})` : '',
      renderCell: (params: GridRenderCellParams) => (
        params.value ? (
          <Box>
            <Typography variant="body2" component="span" fontWeight="medium">{params.value.count}</Typography>
            <Typography variant="caption" color="text.secondary" component="span" sx={{ml: 0.5}}>($${params.value.value.toFixed(0)})</Typography>
          </Box>
        ) : null
      )
    },
    {
      field: 'timeValue',
      headerName: 'Time Value',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams) => (
        <TimeValueBadge timeValue={params.value as number} />
      ),
    },
    {
      field: 'pnlToday',
      headerName: 'P&L Today',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams) => (
        params.value ? (
          <Typography 
            variant="body2" 
            fontWeight="medium" 
            sx={{ 
              color: (params.value as string).startsWith('-') 
                ? theme.palette.error.main 
                : theme.palette.success.main 
            }}
          >
            {params.value}
          </Typography>
        ) : null
      ),
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 100,
      cellClassName: 'actions',
      getActions: ({ row }: { row: any }) => [
        <GridActionsCellItem
          icon={<EditIcon />}
          label="Edit"
          onClick={() => { console.log("Edit", row.id); handleOpenAddDialog(); /* Pass follower data to dialog */ }}
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


  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
            Followers Management
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Manage and monitor all trading followers
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={handleOpenAddDialog}>
          Add New Follower
        </Button>
      </Box>

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
                <MenuItem value="WARN">Warning</MenuItem>
                <MenuItem value="ERROR">Error</MenuItem>
              </Select>
            </FormControl>
          </Grid2>
          <Grid2 size={{xs: 6, sm: 3, md: 2}}>
             <FormControl fullWidth size="small">
              <InputLabel>Bot Status</InputLabel>
              <Select defaultValue="ALL" label="Bot Status">
                <MenuItem value="ALL">All</MenuItem>
                <MenuItem value="ONLINE">Online</MenuItem>
                <MenuItem value="OFFLINE">Offline</MenuItem>
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

      <Paper sx={{ width: '100%', overflow: 'hidden', position: 'relative' }}>
        {loading && (
          <Box sx={{ 
            position: 'absolute', 
            top: 0, 
            left: 0, 
            right: 0, 
            bottom: 0, 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            backgroundColor: 'rgba(255, 255, 255, 0.8)',
            zIndex: 1
          }}>
            <CircularProgress />
          </Box>
        )}
        {error && (
          <Alert severity="error" sx={{ m: 2 }}>
            {error}
            <Button size="small" onClick={refresh} sx={{ ml: 2 }}>Retry</Button>
          </Alert>
        )}
        <DataGrid
          rows={displayFollowers}
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
              backgroundColor: alpha(theme.palette.primary.main, 0.05),
            },
            '& .MuiDataGrid-row': {
              '&:hover': {
                backgroundColor: alpha(theme.palette.primary.main, 0.05)
              }
            }
          }}
          getRowId={(row) => row.id}
        />
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', p: 1, borderTop: 1, borderColor: 'divider' }}>
          <Button 
            startIcon={<RefreshIcon />} 
            size="small" 
            onClick={refresh}
            disabled={loading}
          >
            Refresh
          </Button>
        </Box>
      </Paper>

      {expandedRow && displayFollowers.find(f => f.id === expandedRow) && (
        <Collapse in={!!expandedRow} timeout="auto" unmountOnExit sx={{mt: 1}}>
            <ExpandedFollowerDetail follower={displayFollowers.find(f => f.id === expandedRow)!} />
        </Collapse>
      )}
      
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
          <MenuItem onClick={() => handleConfirmAction(actionFollower, 'DISABLE')} sx={{color: 'warning.main'}}>
            <ListItemIcon><HighlightOffIcon fontSize="small" color="warning" /></ListItemIcon>
            <ListItemText>Disable</ListItemText>
          </MenuItem>
          <MenuItem onClick={() => handleConfirmAction(actionFollower, 'CLOSE_POSITIONS')} sx={{color: 'error.main'}}>
            <ListItemIcon><CloseIcon fontSize="small" color="error" /></ListItemIcon>
            <ListItemText>Close Positions</ListItemText>
          </MenuItem>
        </Menu>
      )}

      <Dialog open={openAddDialog} onClose={handleCloseAddDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Add New Follower</DialogTitle>
        <DialogContent>
          {/* Add form fields here based on mockup */}
          <TextField margin="dense" label="Follower ID" type="text" fullWidth variant="outlined" />
          <TextField margin="dense" label="IB Account ID" type="text" fullWidth variant="outlined" />
          <TextField margin="dense" label="Description" type="text" fullWidth variant="outlined" multiline rows={2}/>
          {/* ... more fields */}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseAddDialog}>Cancel</Button>
          <Button onClick={handleCloseAddDialog} variant="contained">Save Follower</Button>
        </DialogActions>
      </Dialog>

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
              value={pinValue}
              onChange={(e) => setPinValue(e.target.value)}
              error={!!actionError}
              helperText={actionError}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseConfirmDialog} disabled={actionLoading}>Cancel</Button>
          <Button 
            onClick={executeConfirmedAction} 
            variant="contained" 
            color={actionType === 'CLOSE_POSITIONS' ? "error" : "primary"}
            disabled={actionLoading}
          >
            {actionLoading ? <CircularProgress size={20} /> : `Confirm ${actionType?.toLowerCase().replace('_', ' ')}`}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={restartDialogOpen} onClose={() => setRestartDialogOpen(false)}>
        <DialogTitle>Restart Service</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to restart the {restartService} service?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRestartDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleServiceRestart} variant="contained" color="warning">
            Restart
          </Button>
        </DialogActions>
      </Dialog>

    </Container>
  );
};

export default FollowersPage;

const ExpandedFollowerDetail: React.FC<{ follower: any }> = ({ follower }) => {
  const theme = useTheme();
  const chartData = [
    { name: 'Jan', pnl: Math.random() * 2000 + 1000 }, { name: 'Feb', pnl: Math.random() * 2000 + 1000 },
    { name: 'Mar', pnl: Math.random() * 2000 + 1000 }, { name: 'Apr', pnl: Math.random() * 2000 + 1000 },
    { name: 'May', pnl: Math.random() * 2000 + 1000 }, { name: 'Jun', pnl: Math.random() * 2000 + 1000 },
  ];

  return (
    <Box sx={{ p: 2, bgcolor: alpha(theme.palette.primary.light, 0.05), borderTop: `1px solid ${theme.palette.divider}` }}>
      <Grid2 container spacing={2}>
        <Grid2 size={{xs: 12, md: 4}}>
          <Typography variant="subtitle2" gutterBottom color="text.secondary">ACCOUNT DETAILS</Typography>
          <Paper variant="outlined" sx={{p:2}}>
            <Typography variant="body2"><strong>Name:</strong> {follower.name || 'N/A'}</Typography>
            <Typography variant="body2"><strong>Email:</strong> {follower.email || 'N/A'}</Typography>
            <Typography variant="body2"><strong>Commission:</strong> {follower.commission_pct || 0}%</Typography>
          </Paper>
        </Grid2>
        <Grid2 size={{xs: 12, md: 4}}>
          <Typography variant="subtitle2" gutterBottom color="text.secondary">PERFORMANCE</Typography>
           <Paper variant="outlined" sx={{p:2}}>
            <Typography variant="body2"><strong>P&L Today:</strong>
              <Typography component="span" sx={{ color: follower.pnlToday.startsWith('-') ? theme.palette.trading.loss : theme.palette.trading.profit, fontWeight: 'medium' }}> {follower.pnlToday}</Typography>
            </Typography>
            <Typography variant="body2"><strong>P&L MTD:</strong>
              <Typography component="span" sx={{ color: follower.pnlMtd.startsWith('-') ? theme.palette.trading.loss : theme.palette.trading.profit, fontWeight: 'medium' }}> {follower.pnlMtd}</Typography>
            </Typography>
            <Typography variant="body2"><strong>P&L Total:</strong>
              <Typography component="span" sx={{ color: follower.pnlTotal < 0 ? theme.palette.error.main : theme.palette.success.main, fontWeight: 'medium' }}> ${follower.pnlTotal?.toFixed(2) || '0.00'}</Typography>
            </Typography>
            <Box sx={{ height: 100, mt: 1 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 0, left: -30, bottom: 5 }}>
                  <YAxis tick={{ fontSize: 10 }} />
                  <Line type="monotone" dataKey="pnl" stroke={theme.palette.primary.main} strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </Box>
          </Paper>
        </Grid2>
        <Grid2 size={{xs: 12, md: 4}}>
          <Typography variant="subtitle2" gutterBottom color="text.secondary">POSITIONS ({follower.positions?.count || 0})</Typography>
          <Paper variant="outlined" sx={{p:2}}>
            <Typography variant="body2"><strong>Count:</strong> {follower.positions?.count || 0}</Typography>
            <Typography variant="body2"><strong>Value:</strong> ${follower.positions?.value?.toFixed(2) || '0.00'}</Typography>
          </Paper>
        </Grid2>
      </Grid2>
    </Box>
  );
};
// This line and everything after it is part of the old structure and should be removed.