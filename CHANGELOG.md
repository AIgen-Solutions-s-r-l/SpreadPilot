# Changelog

All notable changes to SpreadPilot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.1.5.0] - 2025-06-28

### Added
- **Real-time P&L System**: Comprehensive PostgreSQL-based P&L tracking with 30-second MTM calculations
- **PostgreSQL Integration**: New database layer with SQLAlchemy models and Alembic migrations
- **Automated Rollups**: Daily P&L summaries at 16:30 ET and monthly at 00:10 ET with performance metrics
- **Trade & Quote Recording**: Complete trade execution and market data storage system
- **P&L Service**: Dedicated service for monitoring, calculation, and aggregation of profit/loss data
- **Enhanced Documentation**: Updated architecture diagrams and system documentation

### Enhanced
- **Trading Bot Integration**: P&L service seamlessly integrated with existing trading architecture
- **Database Infrastructure**: Dual database architecture with MongoDB for trading data and PostgreSQL for P&L analytics
- **Comprehensive Testing**: 18 unit tests covering P&L service functionality and edge cases

## [v1.1.4.0] - 2025-06-28

### Added
- **Time Value Monitor**: RISK-2.1 implementation with automated liquidation when time value < $0.10
- **Risk Status Management**: SAFE/RISK/CRITICAL status tracking in Redis with real-time updates
- **Automated Liquidation**: Market order execution for positions when time value threshold is breached
- **Alert Integration**: Comprehensive alert publishing for risk status changes and liquidation events
- **60-Second Monitoring**: Continuous time value monitoring during market hours

### Enhanced
- **Time Value Calculation**: TV = spread_mark_price - intrinsic_value with comprehensive error handling
- **Redis Integration**: Real-time status publishing and caching for follower risk monitoring
- **Test Coverage**: 16 comprehensive unit tests for time value monitoring functionality

## [v1.1.3.0] - 2025-06-27

### Added
- **Signal Listener Service**: Scheduled service that polls Google Sheets at 09:27 EST daily for trading signals
- **Redis Pub/Sub Integration**: Real-time signal distribution between Signal Listener and Trading Bot
- **Advanced Order Execution**: Enhanced VerticalSpreadExecutor with comprehensive limit-ladder strategy
- **Comprehensive Testing**: Extensive unit test suites for both signal processing and order execution
- **APScheduler Integration**: Timezone-aware scheduling for US/Eastern time zone
- **Signal Model**: Complete Signal dataclass with Redis serialization support

### Enhanced
- **Order Execution Flow**: Pre-trade margin checks, MID price validation, and incremental pricing
- **Trading Architecture**: Updated data flow to include Redis Pub/Sub signal processing
- **System Documentation**: Updated architecture diagrams and component descriptions
- **Test Infrastructure**: Improved test setup with mocked dependencies and isolated testing

### Fixed
- **Import Paths**: Updated test import paths for better module resolution
- **Test Dependencies**: Enhanced test environment setup and dependency management

## [v1.1.2.0] - 2025-06-27

### Added
- **HashiCorp Vault Integration**: Secure credential management for IBKR credentials and sensitive configuration
- **Docker Compose Infrastructure**: Complete infrastructure setup with PostgreSQL, Vault, MinIO, and Traefik services
- **Vault Client Library**: Comprehensive `VaultClient` utility class with KV v2 secrets engine support
- **Infrastructure Automation**: Management scripts for infrastructure lifecycle and health monitoring
- **Unit Test Coverage**: Comprehensive test suite with mocked hvac Client for Vault integration

### Enhanced
- **Credential Management**: Vault-first approach with fallback to existing credential systems
- **Gateway Manager**: Integrated Vault credential retrieval for IBGateway container startup
- **Trading Bot Configuration**: Added Vault configuration fields and credential retrieval methods
- **System Architecture**: Updated documentation and diagrams to reflect Vault integration
- **Development Environment**: Infrastructure services managed separately from application services

### Technical Implementation
- **VaultClient Class**: Centralized Vault operations with authentication and health checking
- **Configuration Integration**: Environment variable configuration for Vault endpoint and authentication
- **Follower-Specific Credentials**: Support for per-follower secret references in Vault
- **Backward Compatibility**: Graceful degradation when Vault is unavailable or disabled
- **Infrastructure Scripts**: `compose-up.sh`, `compose-down.sh`, and `health-check.sh` for complete automation

### Security Features
- **Secure Secret Storage**: IBKR credentials stored in Vault instead of environment variables
- **Development Mode**: Vault development mode for local testing with automatic secret initialization
- **Access Control**: Structured secret paths for different strategies and followers
- **SSL/TLS Support**: Configurable SSL verification for production Vault deployments

This release adds enterprise-grade secret management and infrastructure automation, significantly enhancing security and operational capabilities.

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