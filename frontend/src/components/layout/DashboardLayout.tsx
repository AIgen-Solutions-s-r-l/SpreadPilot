import React, { useState } from 'react';
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Typography,
  Box,
  Avatar,
  Menu,
  MenuItem,
  Divider,
  useTheme,
  useMediaQuery,
  Tooltip as MuiTooltip,
  Stack,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  People as PeopleIcon,
  TrendingUp as TrendingUpIcon,
  Article as ArticleIcon,
  Terminal as TerminalIcon,
  Menu as MenuIcon,
  Notifications as NotificationsIcon,
  AccountCircle as AccountCircleIcon,
  Logout as LogoutIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';

const drawerWidth = 250;

interface DashboardLayoutProps {
  children?: React.ReactNode;
}

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactElement;
}

const navItems: NavItem[] = [
  { path: '/dashboard', label: 'Dashboard', icon: <DashboardIcon /> },
  { path: '/followers', label: 'Followers', icon: <PeopleIcon /> },
  { path: '/trading-activity', label: 'Trading Activity', icon: <TrendingUpIcon /> },
  { path: '/logs', label: 'Logs', icon: <ArticleIcon /> },
  { path: '/commands', label: 'Commands', icon: <TerminalIcon /> },
];

const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorElUser, setAnchorElUser] = useState<null | HTMLElement>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const theme = useTheme();
  const isMdUp = useMediaQuery(theme.breakpoints.up('md'));

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleOpenUserMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorElUser(event.currentTarget);
  };

  const handleCloseUserMenu = () => {
    setAnchorElUser(null);
  };
  
  const handleLogout = () => {
    // Add actual logout logic here
    handleCloseUserMenu();
    navigate('/login');
  };

  const getCurrentPageTitle = () => {
    const currentItem = navItems.find(item => location.pathname.startsWith(item.path));
    return currentItem?.label || 'Dashboard';
  };

  const drawerContent = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Toolbar sx={{ bgcolor: 'primary.darker', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography variant="h6" noWrap component="div" sx={{ color: 'common.white', fontWeight: 'bold' }}>
          SpreadPilot
        </Typography>
      </Toolbar>
      <Divider />
      <List sx={{ flexGrow: 1, pt: 1 }}>
        {navItems.map((item) => (
          <ListItem key={item.path} disablePadding sx={{ display: 'block' }}>
            <ListItemButton
              component={NavLink}
              to={item.path}
              onClick={isMdUp ? undefined : handleDrawerToggle} // Close mobile drawer on click
              sx={{
                minHeight: 48,
                justifyContent: mobileOpen || isMdUp ? 'initial' : 'center',
                px: 2.5,
                borderRadius: 1,
                mx: 1,
                mb: 0.5,
                color: 'primary.contrastText',
                '&.active': {
                  bgcolor: 'primary.main',
                  color: 'primary.contrastText',
                  '& .MuiListItemIcon-root': {
                    color: 'primary.contrastText',
                  },
                },
                '&:hover': {
                  bgcolor: 'primary.light',
                  color: 'primary.contrastText',
                   '& .MuiListItemIcon-root': {
                    color: 'primary.contrastText',
                  },
                },
              }}
            >
              <ListItemIcon
                sx={{
                  minWidth: 0,
                  mr: mobileOpen || isMdUp ? 3 : 'auto',
                  justifyContent: 'center',
                  color: 'inherit',
                }}
              >
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.label} sx={{ opacity: mobileOpen || isMdUp ? 1 : 0, color: 'inherit' }} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      <Divider />
      <Box sx={{ p: 2, mt: 'auto', bgcolor: 'primary.darker' }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Avatar sx={{ bgcolor: 'secondary.main', width: 36, height: 36, mr: 1.5 }}>
            A
          </Avatar>
          <Box>
            <Typography variant="subtitle2" sx={{ color: 'common.white', fontWeight: 'medium' }}>Admin User</Typography>
            <Stack direction="row" spacing={0.5} alignItems="center">
              <IconButton size="small" sx={{p:0.2, color: 'primary.light', '&:hover': {color: 'common.white'}}}>
                <SettingsIcon sx={{fontSize: '1rem'}}/>
              </IconButton>
               <Divider orientation="vertical" flexItem sx={{borderColor: 'primary.main', height: '12px', alignSelf: 'center'}}/>
              <IconButton size="small" sx={{p:0.2, color: 'primary.light', '&:hover': {color: 'common.white'}}} onClick={handleLogout}>
                <LogoutIcon sx={{fontSize: '1rem'}}/>
              </IconButton>
            </Stack>
          </Box>
        </Box>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar
        position="fixed"
        sx={{
          zIndex: theme.zIndex.drawer + 1,
          bgcolor: 'background.paper',
          color: 'text.primary',
          boxShadow: theme.shadows[1]
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1, fontWeight: 'medium' }}>
            {getCurrentPageTitle()}
          </Typography>
          <MuiTooltip title="Notifications">
            <IconButton color="inherit" sx={{mr: 1}}>
              <NotificationsIcon />
            </IconButton>
          </MuiTooltip>
          <MuiTooltip title="Account settings">
            <IconButton onClick={handleOpenUserMenu} sx={{ p: 0 }}>
              <Avatar alt="Admin User" sx={{ bgcolor: 'primary.main' }}>A</Avatar>
            </IconButton>
          </MuiTooltip>
          <Menu
            sx={{ mt: '45px' }}
            id="menu-appbar"
            anchorEl={anchorElUser}
            anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
            keepMounted
            transformOrigin={{ vertical: 'top', horizontal: 'right' }}
            open={Boolean(anchorElUser)}
            onClose={handleCloseUserMenu}
          >
            <MenuItem onClick={handleCloseUserMenu}>
              <ListItemIcon><AccountCircleIcon fontSize="small" /></ListItemIcon>
              <ListItemText>Profile</ListItemText>
            </MenuItem>
            <MenuItem onClick={handleCloseUserMenu}>
               <ListItemIcon><SettingsIcon fontSize="small" /></ListItemIcon>
              <ListItemText>Settings</ListItemText>
            </MenuItem>
            <Divider />
            <MenuItem onClick={handleLogout}>
              <ListItemIcon><LogoutIcon fontSize="small" /></ListItemIcon>
              <ListItemText>Logout</ListItemText>
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>
      
      <Drawer
        variant={isMdUp ? "permanent" : "temporary"}
        open={isMdUp ? true : mobileOpen}
        onClose={handleDrawerToggle}
        ModalProps={{ keepMounted: true }} // Better open performance on mobile.
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: {
            width: drawerWidth,
            boxSizing: 'border-box',
            bgcolor: 'primary.dark', // Darker shade for sidebar
            color: 'primary.contrastText',
            borderRight: 'none',
            boxShadow: theme.shadows[2]
          },
        }}
      >
        {drawerContent}
      </Drawer>
      
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          bgcolor: 'background.default',
          p: 3,
          width: { md: `calc(100% - ${drawerWidth}px)` },
          mt: '64px', // AppBar height
          overflow: 'auto'
        }}
      >
        {/* <Toolbar />  // This was for when AppBar was not fixed, remove if AppBar is fixed */}
        {children || <Outlet />}
      </Box>
    </Box>
  );
};

export default DashboardLayout;