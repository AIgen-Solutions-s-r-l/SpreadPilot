# Original EMA Strategy Paper Trading Test Plan

## Overview

This document outlines the plan for paper trading the Original EMA Crossover Strategy implementation in SpreadPilot. The purpose of paper trading is to validate the strategy's implementation against the original system's behavior in a real-time market environment without risking actual capital.

## 1. Setup Instructions

### 1.1 Environment Configuration

1. **IBKR Paper Trading Account Setup**:
   - Ensure you have an active Interactive Brokers paper trading account
   - Verify the account has sufficient paper funds (minimum $25,000 recommended)
   - Configure the account to trade SOXS and SOXL without restrictions

2. **IB Gateway Configuration**:
   - Install the latest version of IB Gateway
   - Configure IB Gateway to connect to the paper trading environment
   - Set up automatic login with the paper trading credentials
   - Configure IB Gateway to accept API connections from localhost

3. **SpreadPilot Configuration**:
   - Update `trading-bot/app/config.py` with the following settings:
     ```python
     ORIGINAL_EMA_STRATEGY = {
         "enabled": True,
         "ibkr_secret_ref": "ibkr_original_strategy_paper",  # Secret reference for paper trading credentials
         "symbols": ["SOXS", "SOXL"],
         "fast_ema": 7,
         "slow_ema": 21,
         "bar_period": "5 mins",
         "trading_start_time": "09:30:00",
         "trading_end_time": "15:29:00",
         "dollar_amount": 10000,  # Adjust based on paper account size
         "trailing_stop_pct": 1.0,
         "close_at_eod": True
     }
     ```
   - Create the secret in Google Secret Manager with the paper trading credentials
   - Configure logging to capture detailed information during the test

### 1.2 Deployment

1. **Local Deployment**:
   - Start IB Gateway and log in to the paper trading account
   - Run the trading-bot service locally:
     ```bash
     cd trading-bot
     python -m app.main
     ```
   - Verify the service connects to IB Gateway successfully
   - Confirm the OriginalStrategyHandler initializes correctly

2. **Cloud Deployment** (optional for extended testing):
   - Deploy the trading-bot service to Google Cloud Run
   - Configure the service to connect to IB Gateway via a secure tunnel
   - Set up appropriate monitoring and logging
   - Ensure the service has access to the required secrets

## 2. Monitoring Procedures

### 2.1 Real-time Monitoring

1. **Log Monitoring**:
   - Monitor the trading-bot logs for:
     - Strategy initialization
     - Historical data fetching
     - EMA calculations
     - Crossover detections
     - Order placements
     - Order fills
     - Trailing stop adjustments
     - EOD position closings
   - Set up log alerts for errors and warnings

2. **Position Monitoring**:
   - Monitor positions through:
     - IBKR TWS or Account Management interface
     - SpreadPilot logs
     - SpreadPilot alerts (if configured)
   - Track position changes in real-time
   - Verify position sizes match the configured dollar amount

3. **Alert Monitoring**:
   - Configure alerts to be sent to:
     - Email
     - Telegram (if configured)
     - Slack (if configured)
   - Verify alerts are received for:
     - Signal generation (crossovers)
     - Order execution
     - Position changes
     - Trailing stop hits
     - EOD position closings

### 2.2 Data Collection

1. **Trade Journal**:
   - Maintain a detailed trade journal with:
     - Entry and exit timestamps
     - Entry and exit prices
     - Position sizes
     - P&L for each trade
     - Signal types that triggered entries and exits
   - Record any discrepancies between expected and actual behavior

2. **Performance Metrics**:
   - Track the following metrics:
     - Win rate
     - Average win/loss
     - Profit factor
     - Maximum drawdown
     - Sharpe ratio
     - Total return
   - Compare these metrics with historical backtests

3. **System Performance**:
   - Monitor system resource usage:
     - CPU and memory usage
     - Network latency
     - API call frequency
     - Response times
   - Identify any performance bottlenecks

## 3. Validation Checkpoints

### 3.1 Signal Generation Validation

1. **EMA Calculation Accuracy**:
   - Verify EMA values match those calculated by external tools (e.g., TradingView)
   - Check for any discrepancies in EMA values at crossover points
   - Ensure EMA calculations use the correct parameters (7 and 21 periods)

2. **Crossover Detection**:
   - Verify all crossovers are correctly identified
   - Check for false positives (detected crossovers that didn't actually occur)
   - Check for false negatives (missed crossovers that should have been detected)
   - Validate the timing of crossover detection

3. **Trading Hours Compliance**:
   - Verify the strategy only trades during configured trading hours
   - Check that no signals are processed outside of trading hours
   - Validate EOD position closing occurs at the specified time

### 3.2 Order Execution Validation

1. **Order Creation**:
   - Verify market orders are created correctly for entries
   - Verify trailing stop orders are created with the correct parameters
   - Check that order quantities match the expected position sizes

2. **Order Routing**:
   - Verify orders are routed to the correct exchange
   - Check for any order routing issues or delays
   - Validate that orders are executed in a timely manner

3. **Position Management**:
   - Verify positions are updated correctly after order fills
   - Check that position sizes match the configured dollar amount
   - Validate that positions are closed correctly at EOD if configured

### 3.3 Risk Management Validation

1. **Trailing Stop Functionality**:
   - Verify trailing stops are placed correctly after entries
   - Check that trailing stops are adjusted as prices move favorably
   - Validate that trailing stops trigger correctly when prices reverse

2. **EOD Position Closing**:
   - Verify all positions are closed at the end of the trading day
   - Check that closing orders are executed correctly
   - Validate that no positions remain open overnight

3. **Error Handling**:
   - Test error scenarios (e.g., connection loss, order rejection)
   - Verify the system recovers gracefully from errors
   - Check that appropriate alerts are generated for errors

## 4. Comparison Methodology with Original System

### 4.1 Side-by-Side Comparison

1. **Signal Comparison**:
   - Run both systems (original and SpreadPilot) simultaneously
   - Compare signals generated by both systems
   - Record any differences in signal timing or type
   - Analyze the causes of any discrepancies

2. **Trade Comparison**:
   - Compare trades executed by both systems
   - Analyze differences in:
     - Entry and exit times
     - Entry and exit prices
     - Position sizes
     - P&L for each trade
   - Identify patterns in any discrepancies

3. **Performance Comparison**:
   - Compare performance metrics between the two systems
   - Analyze differences in:
     - Win rate
     - Average win/loss
     - Profit factor
     - Maximum drawdown
     - Sharpe ratio
     - Total return
   - Determine if differences are statistically significant

### 4.2 Root Cause Analysis

1. **Discrepancy Investigation**:
   - For each significant discrepancy, investigate:
     - Data sources and quality
     - Calculation methodologies
     - Timing differences
     - Order execution differences
     - System latency
   - Document findings and potential improvements

2. **Implementation Refinement**:
   - Based on the analysis, refine the SpreadPilot implementation to more closely match the original system
   - Prioritize fixes based on impact on performance
   - Implement changes incrementally and validate after each change

3. **Documentation**:
   - Document any inherent differences between the systems that cannot be eliminated
   - Provide explanations for these differences
   - Assess the impact of these differences on overall performance

## 5. Test Duration and Success Criteria

### 5.1 Test Duration

1. **Initial Test Phase**:
   - Duration: 2 weeks
   - Focus: System stability, signal generation, order execution
   - Goal: Identify and fix any critical issues

2. **Extended Test Phase**:
   - Duration: 4 weeks
   - Focus: Performance comparison with original system
   - Goal: Fine-tune implementation to match original system

3. **Final Validation Phase**:
   - Duration: 2 weeks
   - Focus: Comprehensive validation of all aspects
   - Goal: Confirm readiness for production deployment

### 5.2 Success Criteria

1. **Technical Criteria**:
   - 100% of crossovers correctly identified
   - Order execution latency < 1 second
   - No system errors or crashes
   - All positions correctly managed
   - All trailing stops functioning correctly
   - EOD position closing working as expected

2. **Performance Criteria**:
   - Signal timing within 5 seconds of original system
   - Trade execution prices within 0.1% of original system
   - Performance metrics within 5% of original system
   - No unexplained discrepancies between systems

3. **Operational Criteria**:
   - All monitoring systems functioning correctly
   - Alerts generated for all significant events
   - System resource usage within acceptable limits
   - No manual intervention required during normal operation

## 6. Reporting and Decision Making

### 6.1 Regular Reporting

1. **Daily Reports**:
   - Summary of signals and trades
   - Performance metrics
   - System status
   - Any issues or discrepancies

2. **Weekly Reports**:
   - Detailed performance analysis
   - Comparison with original system
   - Progress on issue resolution
   - Recommendations for improvements

3. **Final Report**:
   - Comprehensive analysis of test results
   - Detailed comparison with original system
   - Assessment against success criteria
   - Recommendation for production deployment

### 6.2 Decision Points

1. **End of Initial Phase**:
   - Decision: Continue to Extended Phase or extend Initial Phase
   - Criteria: No critical issues, basic functionality working correctly

2. **End of Extended Phase**:
   - Decision: Continue to Final Phase or extend Extended Phase
   - Criteria: Performance closely matching original system, no significant discrepancies

3. **End of Final Phase**:
   - Decision: Approve for production or extend testing
   - Criteria: All success criteria met, no outstanding issues

## 7. Contingency Planning

### 7.1 Issue Response

1. **Critical Issues**:
   - Immediately stop the test
   - Investigate and fix the issue
   - Restart the test from the beginning

2. **Major Issues**:
   - Continue the test if possible
   - Investigate and fix the issue
   - Document the impact on test results

3. **Minor Issues**:
   - Continue the test
   - Fix the issue in parallel
   - Document the issue for future improvements

### 7.2 Test Extension

1. **Criteria for Extension**:
   - Significant discrepancies with original system
   - Unresolved issues affecting performance
   - Insufficient data for conclusive analysis

2. **Extension Process**:
   - Document reasons for extension
   - Define specific goals for the extension period
   - Set new timeline and success criteria

## 8. Post-Test Activities

### 8.1 Documentation

1. **Test Results Documentation**:
   - Comprehensive report of test results
   - Analysis of discrepancies and their causes
   - Performance comparison with original system
   - Recommendations for future improvements

2. **Implementation Documentation**:
   - Update technical documentation with any changes made during testing
   - Document any known limitations or differences from original system
   - Provide operational guidelines for production deployment

### 8.2 Knowledge Transfer

1. **Team Briefing**:
   - Present test results to the development and operations teams
   - Discuss lessons learned and best practices
   - Address any questions or concerns

2. **Customer Communication**:
   - Prepare summary of test results for customer
   - Highlight any differences from original system
   - Provide recommendations for production deployment

## Appendix A: Test Environment Details

- **IBKR Paper Trading Account**: [Account ID]
- **IB Gateway Version**: [Version]
- **SpreadPilot Version**: [Version]
- **Test Coordinator**: [Name]
- **Test Period**: [Start Date] to [End Date]
- **Reporting Frequency**: Daily summary, Weekly detailed report
- **Communication Channels**: [Email/Slack/Teams]

## Appendix B: Test Data Collection Templates

### B.1 Daily Trading Log Template

| Date | Time | Symbol | Signal Type | Action | Quantity | Price | P&L | Notes |
|------|------|--------|------------|--------|----------|-------|-----|-------|
|      |      |        |            |        |          |       |     |       |

### B.2 System Performance Log Template

| Date | CPU Usage (%) | Memory Usage (MB) | API Calls | Response Time (ms) | Errors | Warnings |
|------|---------------|-------------------|-----------|-------------------|--------|----------|
|      |               |                   |           |                   |        |          |

### B.3 Comparison Log Template

| Date | Time | Signal | SpreadPilot Action | Original System Action | Difference | Root Cause |
|------|------|--------|-------------------|------------------------|------------|------------|
|      |      |        |                   |                        |            |            |