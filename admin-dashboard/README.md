# SpreadPilot Admin Dashboard

A mobile-responsive Vue 3 + Vite single-page application for managing the SpreadPilot trading platform.

## Features

- 📱 **Mobile-First Design**: Fully responsive interface optimized for mobile devices
- 🔐 **Authentication**: Secure login with JWT token management
- 👥 **Followers Management**: View and manage trading followers with real-time data
- 📊 **Real-Time Time Value Monitoring**: Color-coded risk badges (SAFE/RISK/CRITICAL)
- 📝 **System Logs**: Real-time log streaming with filtering capabilities
- ⚙️ **Settings**: Configurable system parameters and notification preferences
- 🎨 **Modern UI**: Built with Tailwind CSS for a clean, professional interface

## Technology Stack

- **Vue 3**: Modern reactive framework with Composition API
- **Vite**: Lightning-fast development server and build tool
- **Vue Router**: Client-side routing for SPA navigation
- **Tailwind CSS**: Utility-first CSS framework for rapid UI development
- **Axios**: Promise-based HTTP client for API communication

## Project Setup

### Prerequisites

- Node.js 18+ (though it will work with warnings on v18)
- npm or yarn
- SpreadPilot Admin API running on port 8002

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Update .env with your API URL
VITE_API_URL=http://localhost:8002/api
```

### Development

```bash
# Start development server with hot-reload
npm run dev

# The app will be available at http://localhost:3001
```

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
admin-dashboard/
├── src/
│   ├── components/         # Reusable Vue components
│   │   ├── Layout.vue     # Main app layout with navigation
│   │   └── TimeValueBadge.vue # Risk level indicator component
│   ├── composables/       # Vue composition functions
│   │   └── useTimeValue.js # Real-time time value monitoring
│   ├── router/            # Vue Router configuration
│   ├── services/          # API service layer
│   │   └── api.js        # Axios instance and API endpoints
│   ├── views/             # Page components
│   │   ├── Login.vue     # Authentication page
│   │   ├── Followers.vue # Followers management
│   │   ├── Logs.vue      # System logs viewer
│   │   └── Settings.vue  # Configuration page
│   ├── App.vue           # Root component
│   ├── main.js           # Application entry point
│   └── style.css         # Global styles (Tailwind imports)
├── public/               # Static assets
├── index.html           # HTML template
├── vite.config.js       # Vite configuration
├── tailwind.config.js   # Tailwind CSS configuration
└── postcss.config.js    # PostCSS configuration
```

## API Integration

The dashboard connects to the SpreadPilot Admin API with the following endpoints:

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout

### Followers
- `GET /api/followers` - List all followers
- `GET /api/followers/:id` - Get follower details
- `POST /api/followers` - Create new follower
- `PUT /api/followers/:id` - Update follower
- `DELETE /api/followers/:id` - Delete follower
- `GET /api/pnl/follower/:id` - Get follower P&L data

### Logs
- `GET /api/logs` - Get system logs with filtering
- `GET /api/logs/follower/:id` - Get logs for specific follower

### Settings
- `GET /api/settings` - Get current settings
- `PUT /api/settings` - Update settings

## Key Features

### Mobile Navigation
The app features a responsive navigation system:
- Desktop: Fixed sidebar navigation
- Mobile: Hamburger menu with slide-out drawer

### Real-Time Updates
- Time value badges poll every 30 seconds
- System logs refresh every 5 seconds
- Configurable polling intervals in settings

### Risk Level Indicators
Time values are color-coded based on thresholds:
- 🟢 **SAFE**: Time value ≥ $0.10
- 🟡 **RISK**: Time value between $0.05 and $0.10
- 🔴 **CRITICAL**: Time value < $0.05

### Authentication Flow
- Login credentials are sent to the API
- JWT token is stored in localStorage
- Token is included in all API requests
- Automatic redirect to login on 401 errors

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Admin API base URL | `http://localhost:8002/api` |

## Development Tips

### API Proxy
During development, Vite is configured to proxy `/api` requests to the backend:
```js
proxy: {
  '/api': {
    target: 'http://localhost:8002',
    changeOrigin: true,
  }
}
```

### Tailwind CSS
- Use utility classes for styling
- Responsive modifiers: `sm:`, `md:`, `lg:`, `xl:`
- Forms plugin is included for better form styling

### Vue Composition API
- Components use `<script setup>` syntax
- Composables for reusable logic (e.g., `useTimeValue`)
- Reactive state management with `ref` and `computed`

## Deployment

### Docker

Create a Dockerfile for containerized deployment:

```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

### Environment Configuration

For production, update the API URL:
```bash
VITE_API_URL=https://api.spreadpilot.com/api
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Run `npm run build` to ensure production build works
4. Submit a pull request

## License

Part of the SpreadPilot trading platform.