import { createTheme, responsiveFontSizes } from '@mui/material/styles';

// Color palette for financial/trading platform
const palette = {
  primary: {
    main: '#3B82F6', // Primary blue
    light: '#60A5FA',
    dark: '#2563EB',
    contrastText: '#FFFFFF',
  },
  secondary: {
    main: '#6B7280', // Neutral gray
    light: '#9CA3AF',
    dark: '#4B5563',
    contrastText: '#FFFFFF',
  },
  success: {
    main: '#10B981', // Green for profits/positive values
    light: '#34D399',
    dark: '#059669',
    contrastText: '#FFFFFF',
  },
  error: {
    main: '#EF4444', // Red for losses/negative values
    light: '#F87171',
    dark: '#DC2626',
    contrastText: '#FFFFFF',
  },
  warning: {
    main: '#F59E0B', // Amber for warnings
    light: '#FBBF24',
    dark: '#D97706',
    contrastText: '#FFFFFF',
  },
  info: {
    main: '#3B82F6', // Blue for information
    light: '#60A5FA',
    dark: '#2563EB',
    contrastText: '#FFFFFF',
  },
  background: {
    default: '#F3F4F6', // Light gray background
    paper: '#FFFFFF',
  },
  text: {
    primary: '#1F2937',
    secondary: '#4B5563',
    disabled: '#9CA3AF',
  },
  divider: '#E5E7EB',
  // Custom colors for trading platform
  trading: {
    profit: '#10B981', // Green for profits
    loss: '#EF4444', // Red for losses
    neutral: '#6B7280', // Gray for neutral
    buy: '#3B82F6', // Blue for buy actions
    sell: '#8B5CF6', // Purple for sell actions
  },
};

// Typography settings
const typography = {
  fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  h1: {
    fontWeight: 700,
    fontSize: '2.5rem',
  },
  h2: {
    fontWeight: 700,
    fontSize: '2rem',
  },
  h3: {
    fontWeight: 600,
    fontSize: '1.5rem',
  },
  h4: {
    fontWeight: 600,
    fontSize: '1.25rem',
  },
  h5: {
    fontWeight: 600,
    fontSize: '1rem',
  },
  h6: {
    fontWeight: 600,
    fontSize: '0.875rem',
  },
  subtitle1: {
    fontSize: '1rem',
    fontWeight: 500,
  },
  subtitle2: {
    fontSize: '0.875rem',
    fontWeight: 500,
  },
  body1: {
    fontSize: '1rem',
  },
  body2: {
    fontSize: '0.875rem',
  },
  button: {
    fontWeight: 600,
    textTransform: 'none' as const,
  },
  caption: {
    fontSize: '0.75rem',
  },
  overline: {
    fontSize: '0.75rem',
    textTransform: 'uppercase' as const,
    fontWeight: 600,
    letterSpacing: '0.5px',
  },
};

// Component overrides
const components = {
  MuiButton: {
    styleOverrides: {
      root: {
        borderRadius: 8,
        padding: '8px 16px',
        boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
      },
      contained: {
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
        '&:hover': {
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        },
      },
    },
  },
  MuiCard: {
    styleOverrides: {
      root: {
        borderRadius: 12,
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
        transition: 'box-shadow 0.3s ease-in-out, transform 0.3s ease-in-out',
        '&:hover': {
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        },
      },
    },
  },
  MuiPaper: {
    styleOverrides: {
      root: {
        borderRadius: 12,
      },
    },
  },
  MuiTableCell: {
    styleOverrides: {
      head: {
        fontWeight: 600,
        backgroundColor: '#F9FAFB',
      },
    },
  },
  MuiChip: {
    styleOverrides: {
      root: {
        borderRadius: 8,
      },
    },
  },
  MuiAlert: {
    styleOverrides: {
      root: {
        borderRadius: 8,
      },
    },
  },
  MuiLinearProgress: {
    styleOverrides: {
      root: {
        borderRadius: 4,
        height: 6,
      },
    },
  },
};

// Create the base theme
let theme = createTheme({
  palette: palette as any,
  typography,
  components,
  shape: {
    borderRadius: 8,
  },
  shadows: [
    'none',
    '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
    '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
    '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
    ...Array(19).fill('none'), // Fill the rest with 'none'
  ] as any,
});

// Make typography responsive
theme = responsiveFontSizes(theme);

export default theme;

// Type augmentation for custom colors
declare module '@mui/material/styles' {
  interface Palette {
    trading: {
      profit: string;
      loss: string;
      neutral: string;
      buy: string;
      sell: string;
    };
  }
  
  interface PaletteOptions {
    trading?: {
      profit?: string;
      loss?: string;
      neutral?: string;
      buy?: string;
      sell?: string;
    };
  }
}