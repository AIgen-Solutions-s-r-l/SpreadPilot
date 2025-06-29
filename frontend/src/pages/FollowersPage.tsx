import React, { useState } from 'react';
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
} from '@mui/icons-material';
import { LineChart, Line, YAxis, ResponsiveContainer } from 'recharts';


// Mock Data Type
interface Follower {
  // id is already string
  id: string;
  status: 'ACTIVE' | 'INACTIVE' | 'WARN' | 'ERROR';
  botStatus: 'ONLINE' | 'OFFLINE' | 'WARN' | 'ERROR';
  ibgwStatus: 'CONN' | 'DISC' | 'WARN' | 'ERROR';
  positions: {
    count: number;
    value: string;
  };
  pnlToday: string;
  accountId: string;
  created: string;
  lastActive: string;
  pnlMtd: string;
  pnlYtd: string;
  currentPositions: { symbol: string; shares: number; price: string }[];
}

type FollowerStatus = Follower['status'];
type BotStatus = Follower['botStatus'];
type IBGWStatus = Follower['ibgwStatus'];

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
  const [followers] = useState<Follower[]>([
    { id: 'Follower_001', status: 'ACTIVE', botStatus: 'ONLINE', ibgwStatus: 'CONN', positions: { count: 3, value: '$12.5K' }, pnlToday: '+$1,245.67', accountId: 'IB12345678', created: '2025-01-15', lastActive: '2 min ago', pnlMtd: '+$5,678.90', pnlYtd: '+$12,345.67', currentPositions: [{ symbol: 'SOXL', shares: 100, price: '$45.67' }] },
    { id: 'Follower_002', status: 'INACTIVE', botStatus: 'OFFLINE', ibgwStatus: 'DISC', positions: { count: 0, value: '$0' }, pnlToday: '$0.00', accountId: 'IB87654321', created: '2024-11-20', lastActive: '5 days ago', pnlMtd: '-$250.00', pnlYtd: '+$1,200.00', currentPositions: [] },
    { id: 'Follower_003', status: 'ACTIVE', botStatus: 'WARN', ibgwStatus: 'CONN', positions: { count: 1, value: '$5.1K' }, pnlToday: '-$123.45', accountId: 'IB11223344', created: '2025-03-01', lastActive: '1 hour ago', pnlMtd: '+$1,200.50', pnlYtd: '+$3,500.75', currentPositions: [{ symbol: 'QQQ', shares: 50, price: '$410.25' }] },
    { id: 'Follower_004', status: 'ACTIVE', botStatus: 'ONLINE', ibgwStatus: 'ERROR', positions: { count: 2, value: '$8.2K' }, pnlToday: '+$867.45', accountId: 'IB55667788', created: '2025-02-10', lastActive: '15 min ago', pnlMtd: '+$2,100.00', pnlYtd: '+$6,800.20', currentPositions: [{ symbol: 'TQQQ', shares: 30, price: '$55.12' }, { symbol: 'SPY', shares: 10, price: '$500.50' }] },
  ]);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(5);
  const [openAddDialog, setOpenAddDialog] = useState(false);
  const [openConfirmDialog, setOpenConfirmDialog] = useState(false);
  const [actionFollower, setActionFollower] = useState<Follower | null>(null);
  const [actionType, setActionType] = useState<string | null>(null);

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
  const executeConfirmedAction = () => {
    console.log(`Executing ${actionType} for ${actionFollower?.id}`);
    // Add actual logic here
    handleCloseConfirmDialog();
  };



  const columns: GridColDef<Follower>[] = [
    {
      field: 'id',
      headerName: 'ID',
      flex: 1,
      minWidth: 150,
      renderCell: (params: GridRenderCellParams<any, Follower>) => (
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
      renderCell: (params: GridRenderCellParams<any, FollowerStatus>) => {
        if (params.value === undefined) return null; // Handle undefined case
        const chipProps = getStatusChipProps(params.value, theme);
        return <Chip {...chipProps} size="small" />;
      },
    },
    {
      field: 'botStatus',
      headerName: 'Bot',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams<any, BotStatus>) => {
        if (params.value === undefined) return null; // Handle undefined case
        const chipProps = getStatusChipProps(params.value, theme);
        return <Chip {...chipProps} size="small" />;
      },
    },
    {
      field: 'ibgwStatus',
      headerName: 'IBGW',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams<any, IBGWStatus>) => {
        if (params.value === undefined) return null; // Handle undefined case
        const chipProps = getStatusChipProps(params.value, theme);
        return <Chip {...chipProps} size="small" />;
      },
    },
    {
      field: 'positions',
      headerName: 'Positions',
      flex: 1.2,
      minWidth: 150,
      valueGetter: (value: Follower['positions'] | undefined) => value ? `${value.count} (${value.value})` : '',
      renderCell: (params: GridRenderCellParams<any, Follower['positions']>) => (
        params.value ? (
          <Box>
            <Typography variant="body2" component="span" fontWeight="medium">{params.value.count}</Typography>
            <Typography variant="caption" color="text.secondary" component="span" sx={{ml: 0.5}}>({params.value.value})</Typography>
          </Box>
        ) : null
      )
    },
    {
      field: 'pnlToday',
      headerName: 'P&L Today',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams<any, string>) => (
        params.value ? (
          <Typography variant="body2" fontWeight="medium" sx={{ color: params.value.startsWith('-') ? theme.palette.trading.loss : theme.palette.trading.profit }}>
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
      getActions: ({ row }: { row: Follower }) => [
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
              // cursor: 'pointer', // Click handled by IconButton in ID cell
              '&:hover': {
                backgroundColor: alpha(theme.palette.primary.main, 0.05)
              }
            }
          }}
          // Removed isRowExpandable and renderDetailPanel, will use Collapse below
          getRowId={(row) => row.id}
        />
      </Paper>

      {expandedRow && followers.find(f => f.id === expandedRow) && (
        <Collapse in={!!expandedRow} timeout="auto" unmountOnExit sx={{mt: 1}}>
            <ExpandedFollowerDetail follower={followers.find(f => f.id === expandedRow)!} />
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
            <TextField margin="dense" label="PIN" type="password" fullWidth variant="outlined" sx={{mt:2}}/>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseConfirmDialog}>Cancel</Button>
          <Button onClick={executeConfirmedAction} variant="contained" color={actionType === 'CLOSE_POSITIONS' ? "error" : "primary"}>
            Confirm {actionType?.toLowerCase().replace('_', ' ')}
          </Button>
        </DialogActions>
      </Dialog>

    </Container>
  );
};

export default FollowersPage;

const ExpandedFollowerDetail: React.FC<{ follower: Follower }> = ({ follower }) => {
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
            <Typography variant="body2"><strong>Account ID:</strong> {follower.accountId}</Typography>
            <Typography variant="body2"><strong>Created:</strong> {follower.created}</Typography>
            <Typography variant="body2"><strong>Last Active:</strong> {follower.lastActive}</Typography>
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
            <Typography variant="body2"><strong>P&L YTD:</strong>
              <Typography component="span" sx={{ color: follower.pnlYtd.startsWith('-') ? theme.palette.trading.loss : theme.palette.trading.profit, fontWeight: 'medium' }}> {follower.pnlYtd}</Typography>
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
          <Typography variant="subtitle2" gutterBottom color="text.secondary">CURRENT POSITIONS ({follower.currentPositions.length})</Typography>
          <Paper variant="outlined" sx={{p:2, maxHeight: 200, overflowY: 'auto'}}>
            {follower.currentPositions.length > 0 ? follower.currentPositions.map(p => (
              <Box key={p.symbol} sx={{display: 'flex', justifyContent: 'space-between', mb: 0.5}}>
                <Typography variant="caption"><strong>{p.symbol}</strong> ({p.shares})</Typography>
                <Typography variant="caption">{p.price}</Typography>
              </Box>
            )) : <Typography variant="caption">No active positions</Typography>}
          </Paper>
        </Grid2>
      </Grid2>
    </Box>
  );
};
// This line and everything after it is part of the old structure and should be removed.