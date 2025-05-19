import React from 'react';
import { Card, CardContent, Typography, Box, Chip, SvgIcon } from '@mui/material';
import { ArrowUpward as ArrowUpIcon, ArrowDownward as ArrowDownIcon } from '@mui/icons-material';
import { alpha } from '@mui/material/styles';

interface MetricCardProps {
  title: string;
  value: string;
  change: string;
  icon: React.ReactNode;
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, change, icon }) => {
  const isPositive = !change.startsWith('-');
  
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
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
          <Typography variant="overline" color="text.secondary" gutterBottom>
            {title}
          </Typography>
          <Box
            sx={{
              p: 1.5,
              borderRadius: 2,
              bgcolor: (theme) => alpha(theme.palette.primary.main, 0.1),
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'primary.main',
              fontSize: 24
            }}
          >
            {icon}
          </Box>
        </Box>
        
        <Typography variant="h4" component="div" fontWeight="bold" mb={1}>
          {value}
        </Typography>
        
        <Box display="flex" alignItems="center">
          <Chip
            icon={isPositive ? <ArrowUpIcon fontSize="small" /> : <ArrowDownIcon fontSize="small" />}
            label={change.replace(/[+-]/, '')}
            size="small"
            color={isPositive ? 'success' : 'error'}
            sx={{ 
              fontWeight: 'medium',
              '& .MuiChip-icon': { 
                fontSize: '0.875rem',
                marginLeft: '4px',
              }
            }}
          />
          {change.includes('from') && (
            <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
              {change.split('from')[1].trim()}
            </Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default MetricCard;