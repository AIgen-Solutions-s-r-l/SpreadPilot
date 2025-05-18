# SpreadPilot Spreadsheet Integration

This document provides instructions on how to set up and use the Google Sheets integration for SpreadPilot.

## Overview

SpreadPilot can read trading signals from a Google Sheet. The system looks for a row with the current date and processes the trading signal based on the strategy type.

## Google Sheet Format

Your Google Sheet must include the following columns:

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

### Strategy Types

- **Long Strategy (Bull Put Spread)**: The system reads the strike prices from the 'Buy Put' and 'Sell Put' columns.
- **Short Strategy (Bear Call Spread)**: The system reads the strike prices from the 'Sell Call' and 'Buy Call' columns.

## Configuration

To configure the Google Sheets integration, you need to set the following environment variables:

```
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/your-sheet-id/edit
GOOGLE_SHEETS_API_KEY=your-api-key
```

You can set these variables in your `.env` file or in your deployment environment.

## Testing

To test the Google Sheets integration, you can use the provided test script:

```bash
# Set up the environment variables in .env.test
cp .env.test.example .env.test
# Edit .env.test with your Google Sheet URL and API key
nano .env.test

# Run the test script
python test_sheets_integration.py
```

The test script will:
1. Connect to your Google Sheet
2. Look for a row with the current date
3. Process the trading signal
4. Log the results

## Troubleshooting

If you encounter issues with the Google Sheets integration, check the following:

1. Make sure your Google Sheet is publicly accessible or shared with the service account.
2. Verify that the column names match exactly as specified above.
3. Ensure there is a row with the current date (in NY timezone).
4. Check that the strategy is either "Long" or "Short".
5. Verify that all required fields for the relevant strategy are present.

## Example Sheet

Here's an example of how your sheet should be structured:

| Data | Ticker | Strategia | Quantità per Leg | Buy Put | Sell Put | Sell Call | Buy Call |
|------|--------|-----------|------------------|---------|----------|-----------|----------|
| 2025-05-14 | QQQ | Long | 125 | 486 | 488 | - | - |
| 2025-05-15 | QQQ | Short | 125 | - | - | 492 | 494 |

Note that for a Long strategy, you only need to fill in the Buy Put and Sell Put columns. For a Short strategy, you only need to fill in the Sell Call and Buy Call columns.