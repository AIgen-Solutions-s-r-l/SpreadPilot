# SpreadPilot Spreadsheet Integration Requirements

## Overview

This document outlines the requirements for integrating your spreadsheet with the SpreadPilot trading system. SpreadPilot is an automated trading platform that executes option spread strategies based on signals from Google Sheets. This integration allows your trading signals to be automatically executed across multiple follower accounts.

## Google Sheets Requirements

### 1. Sheet Structure

Your Google Sheet must include the following columns in a header row:

| Column Name | Description | Example |
|-------------|-------------|---------|
| Data | Trading date in YYYY-MM-DD format | 2025-05-14 |
| Ticker | The ticker symbol (currently only QQQ is supported) | QQQ |
| Strategia | Name of the trading strategy (Long or Short) | Long |
| Quantità per Leg | Quantity per leg of the spread | 125 |
| Buy Put | Strike price for the long put option (used for Long strategy) | 486 |
| Sell Put | Strike price for the short put option (used for Long strategy) | 488 |
| Sell Call | Strike price for the short call option (used for Short strategy) | 492 |
| Buy Call | Strike price for the long call option (used for Short strategy) | 494 |

**Important Notes:**
- The header row must contain exactly these column names.
- The system looks for a row with the current date (in NY timezone).
- Currently, only QQQ ticker is supported for trading.
- The system reads the strike prices from the 'Buy Put' and 'Sell Put' columns if the 'Strategia' is 'Long'.
- The system reads the strike prices from the 'Sell Call' and 'Buy Call' columns if the 'Strategia' is 'Short'.
- All required fields for the relevant strategy must be present for the signal to be processed.

### 2. Sheet Access

Your Google Sheet must be:
- Publicly accessible via a URL, OR
- Shared with our service account (we will provide the email address)

### 3. Example Sheet Format

Here's an example of how your sheet should be structured:

| Data | Ticker | Strategia | Quantità per Leg | Buy Put | Sell Put | Sell Call | Buy Call |
|------|--------|-----------|------------------|---------|----------|-----------|----------|
| 2025-05-14 | QQQ | Long | 125 | 486 | 488 | - | - |
| 2025-05-15 | QQQ | Short | 125 | - | - | 492 | 494 |

## Technical Integration Requirements

### 1. Google Sheets API Access

You will need to provide:
- The URL of your Google Sheet
- API access permissions (public or shared with our service account)

### 2. Configuration Details

The following information will be required for the integration:
- Google Sheet URL: The full URL to your trading signals sheet
- Sheet Name: The name of the specific sheet tab containing signals (default is "Sheet1")
- Signal Frequency: How often you will update the sheet with new signals

## Operational Workflow

1. **Signal Creation**: You create trading signals in your Google Sheet following the required format
2. **Signal Detection**: The SpreadPilot Trading Bot polls your sheet at regular intervals (configurable)
3. **Signal Validation**: The system validates the signal format and checks if it's for the current date
4. **Trade Execution**: If a valid signal is found, the system executes the trades for all active followers
5. **Monitoring**: The system monitors the positions and handles assignments/expirations
6. **Reporting**: Performance reports are generated and sent to followers

## Best Practices

1. **Update Timing**: Update your sheet during non-market hours to ensure signals are ready before trading begins
2. **Data Validation**: Use Google Sheets data validation to ensure your signals follow the required format
3. **Backup Signals**: Maintain a backup method for communicating signals in case of integration issues
4. **Testing**: Test the integration thoroughly using paper trading before going live
5. **Monitoring**: Regularly check the SpreadPilot dashboard to ensure signals are being processed correctly

## Security Considerations

1. **Access Control**: Limit edit access to your Google Sheet to authorized personnel only
2. **Audit Trail**: Maintain a separate log of all signals generated for verification purposes
3. **Regular Reviews**: Periodically review the integration to ensure it's functioning as expected

## Next Steps

To proceed with the integration:

1. Set up your Google Sheet following the format described above
2. Share the sheet URL and access permissions with us
3. We will configure the SpreadPilot system to connect to your sheet
4. We will conduct testing to ensure the integration works correctly
5. Once verified, we will activate the integration for live trading

## Support

For any questions or assistance with the integration, please contact our technical support team at [support@spreadpilot.com](mailto:support@spreadpilot.com).