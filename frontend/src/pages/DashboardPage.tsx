import React from 'react';
import { Container, Box } from '@mui/material';
import {
  BarChart as BarChartIcon,
  TrendingUp as TrendingUpIcon,
  AttachMoney as AttachMoneyIcon,
  CompareArrows as CompareArrowsIcon,
  People as PeopleIcon,
  Shield as ShieldIcon
} from '@mui/icons-material';

// Import our custom MUI components
import StatusBanner from '../components/dashboard/StatusBanner';
import MetricCard from '../components/dashboard/MetricCard';
import PerformanceChart from '../components/dashboard/PerformanceChart';
import ActiveFollowersList from '../components/dashboard/ActiveFollowersList';
import TradingActivityTimeline from '../components/dashboard/TradingActivityTimeline';
import RecentAlerts from '../components/dashboard/RecentAlerts';


const DashboardPage: React.FC = () => {
  // Mockup data for Metric Cards with icons
  const metrics = [
    {
      title: 'TOTAL P&L',
      value: '$12,456.78',
      change: '+2.4% from yesterday',
      icon: <AttachMoneyIcon />
    },
    {
      title: "TODAY'S P&L",
      value: '$350.12',
      change: '+0.5% from last hour',
      icon: <TrendingUpIcon />
    },
    {
      title: 'MONTHLY P&L',
      value: '$3,200.50',
      change: '+1.2% from last week',
      icon: <BarChartIcon />
    },
    {
      title: 'ACTIVE POSITIONS',
      value: '15 ($75,320)',
      change: '+2 since yesterday',
      icon: <CompareArrowsIcon />
    },
    {
      title: 'FOLLOWER COUNT',
      value: '12 Active / 15 Total',
      change: '-1 inactive',
      icon: <PeopleIcon />
    },
    {
      title: 'TRADE COUNT (TODAY)',
      value: '42',
      change: '+5 from yesterday avg',
      icon: <ShieldIcon />
    },
  ];

  const handleRefresh = () => {
    console.log('Refreshing dashboard data...');
    // In a real app, this would fetch fresh data
  };

  const handleViewAllFollowers = () => {
    console.log('Navigating to followers page...');
    // In a real app, this would navigate to the followers page
  };

  const handleViewAllActivity = () => {
    console.log('Navigating to trading activity page...');
    // In a real app, this would navigate to the trading activity page
  };

  const handleViewAllAlerts = () => {
    console.log('Navigating to alerts page...');
    // In a real app, this would navigate to the alerts page
  };

  return (
    <Box sx={{ bgcolor: 'background.default', minHeight: '100%', py: 3 }}>
      <Container maxWidth="xl">
        <StatusBanner onRefresh={handleRefresh} />
        
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr', lg: '1fr 1fr 1fr' }, gap: 3, mb: 3 }}>
          {metrics.map((metric) => (
            <Box key={metric.title}>
              <MetricCard
                title={metric.title}
                value={metric.value}
                change={metric.change}
                icon={metric.icon}
              />
            </Box>
          ))}
        </Box>
        
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '2fr 1fr' }, gap: 3, mb: 3 }}>
          <Box>
            <PerformanceChart />
          </Box>
          <Box>
            <ActiveFollowersList onViewAll={handleViewAllFollowers} />
          </Box>
        </Box>
        
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '2fr 1fr' }, gap: 3 }}>
          <Box>
            <TradingActivityTimeline onViewAll={handleViewAllActivity} />
          </Box>
          <Box>
            <RecentAlerts onViewAll={handleViewAllAlerts} />
          </Box>
        </Box>
      </Container>
    </Box>
  );
};

export default DashboardPage;