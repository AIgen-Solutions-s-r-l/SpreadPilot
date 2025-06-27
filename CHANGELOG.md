# Changelog

All notable changes to SpreadPilot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.1.1] - 2025-06-27

### Added
- **Limit-Ladder Order Execution**: Advanced vertical spread execution engine with dynamic pricing strategy
- **Pre-trade Margin Validation**: IB API `whatIf` integration for margin checks before order placement
- **Risk Management**: Automatic rejection when spread MID price falls below 0.70 threshold
- **Alert Integration**: Real-time notifications for execution events and risk conditions
- **Comprehensive Unit Testing**: 15+ test methods covering all execution scenarios with ib_insync mocks

### Enhanced  
- **Order Execution Strategy**: Limit-ladder approach starting at MID price, incrementing by 0.01 every 5 seconds
- **Multi-Strategy Support**: Both Bull Put (Long) and Bear Call (Short) vertical spreads
- **Fill Detection**: Handles successful fills, partial fills, and timeout scenarios
- **Documentation**: Complete order execution guide with API examples and troubleshooting

### Technical Implementation
- **VerticalSpreadExecutor Class**: Core execution engine with margin validation and dynamic pricing
- **Limit-Ladder Algorithm**: Systematic price improvement until fill or threshold breach
- **Error Handling**: Comprehensive exception management with detailed error responses
- **Performance Monitoring**: Execution metrics and detailed logging for analysis

This release adds sophisticated order execution capabilities enabling optimal fill rates while maintaining strict risk controls.

## [v1.1.0] - 2025-06-27

### Added
- **Gateway Manager**: Automatic IBGateway Docker container management for multiple followers
- **Multi-Follower Support**: Isolated IBKR connections with unique port and client ID allocation
- **Container Lifecycle Management**: Automatic startup, health monitoring, and cleanup
- **Exponential Backoff Retry Logic**: Robust connection handling with configurable retry parameters
- **Resource Management**: Dynamic port and client ID allocation with conflict resolution
- **Integration Tests**: Comprehensive test suite with mocked Docker and IB components

### Enhanced
- **System Architecture**: Updated documentation to reflect gateway management
- **Documentation**: Complete Gateway Manager API reference and usage guide
- **Dependencies**: Added `docker>=6.0.0` and `backoff>=2.2.0` for container management
- **Mermaid Diagrams**: Updated system architecture with multiple IBGateway instances

### Technical Implementation
- **GatewayManager Class**: Core class managing Docker containers and IB connections
- **GatewayInstance DataClass**: Container metadata and status tracking
- **Health Monitoring**: Continuous gateway health checks with automatic reconnection
- **Echo Functionality**: Connection validation with "API client connected" feedback
- **Resource Cleanup**: Proper container and connection cleanup on shutdown

This release adds critical multi-follower infrastructure enabling the platform to scale to multiple concurrent users with isolated trading environments.

## [v1.0.0.0] - 2025-06-27

### Added
- **Initial MVP Foundation Release**
- Development environment setup with proper Python dependency management
- Core `spreadpilot-core` library with IBKR client, MongoDB models, and utilities
- Microservices architecture with Docker containerization
- Admin API service with FastAPI and MongoDB integration
- Frontend React application with Material UI components
- Comprehensive test framework with pytest and environment isolation
- Development documentation and CLAUDE.md guidance file
- Proper directory structure for credentials and reports management

### Fixed
- Python dependencies for Linux environment compatibility
- MongoDB driver version conflicts between services
- Development environment test configuration
- Docker build configurations for service deployment
- Pytest configuration with proper asyncio settings

### Technical Highlights
- **Trading Bot**: Core service for QQQ options strategy execution
- **Admin API**: FastAPI backend with follower management capabilities  
- **Frontend**: React/TypeScript dashboard with real-time monitoring
- **Watchdog**: Service health monitoring and restart management
- **Report Worker**: Automated P&L report generation
- **Alert Router**: Multi-channel notification system

### Development Setup
- Virtual environment with resolved dependency conflicts
- Unit tests passing for core functionality
- Docker services building successfully
- Proper git workflow with detailed commit messages
- Environment variable management for local development

This release establishes the foundational architecture and development environment for the SpreadPilot copy-trading platform.