# SPY 200-MA Backtesting Web Application

A Flask-based web application for interactive backtesting of the SPY 200-day moving average strategy.

## Features

- **Interactive Parameter Control**: Adjust SMA period, date range, and initial capital
- **Real-time Backtesting**: Run backtests server-side with progress indicators
- **Interactive Charts**: View equity curves, drawdowns, and trade returns using Plotly
- **Detailed Trade Log**: See all trades with entry/exit dates, prices, and P&L
- **Performance Metrics**: Comprehensive strategy performance analysis
- **Export Functionality**: Download trade logs as CSV files

## Installation

1. Make sure you have the main backtesting script (`spy_200ma_backtesting.py`) in the parent directory
2. Install the required packages:

```bash
pip install -r requirements.txt
```

## Usage

1. Start the Flask application:

```bash
python app.py
```

2. Open your web browser and navigate to `http://localhost:5000`

3. Set your desired parameters:
   - **SMA Period**: Moving average period (default: 200)
   - **Start Date**: Backtest start date (default: 2010-01-01)
   - **End Date**: Backtest end date (default: 2024-12-31)
   - **Initial Capital**: Starting portfolio value (default: $100,000)

4. Click "Run Backtest" to execute the strategy

5. View results:
   - Performance metrics cards
   - Interactive equity curve chart
   - Drawdown analysis
   - Individual trade returns
   - Detailed trade log table

6. Download trade log as CSV for further analysis

## Strategy Details

The web application runs the SPY 200-day moving average strategy:

- **Entry Signal**: Buy SPY when price > 200-day SMA at month end
- **Exit Signal**: Sell SPY when price < 200-day SMA at month end
- **Rebalancing**: End-of-month rebalancing only
- **Position Sizing**: Full portfolio allocation

## Technical Details

- **Backend**: Flask web framework
- **Charts**: Plotly.js for interactive visualizations
- **Data**: Yahoo Finance via yfinance
- **Backtesting**: backtesting.py library
- **Frontend**: Bootstrap 5 + jQuery

## File Structure

```
webapp/
├── app.py              # Flask application
├── templates/
│   └── index.html      # Main web interface
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## API Endpoints

- `GET /`: Main dashboard
- `POST /run_backtest`: Start backtest with parameters
- `GET /get_results`: Poll for backtest results
- `GET /download_trade_log`: Download trade log as CSV

## Troubleshooting

- Ensure the parent directory contains `spy_200ma_backtesting.py`
- Check that all required packages are installed
- Verify internet connection for data download
- Monitor browser console for JavaScript errors 