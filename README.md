# ORB Backtesting Web Application

A Flask-based web application for interactive backtesting of an ORB strategy using backtesting.py

## Features

- **Interactive Parameter Control**: Adjust slippage, commissions
- **Real-time Backtesting**: Run backtests server-side
- **Interactive Charts**: View equity curves, drawdowns, and trade returns using Plotly
- **Detailed Trade Log**: See all trades with entry/exit dates, prices, and P&L
- **Performance Metrics**: Comprehensive strategy performance analysis
- **Export Functionality**: Download trade logs as CSV files

## Installation and Usage

1. Install packages

```bash
pip install -r requirements.txt
```

2. Start the Flask application:

```bash
python app.py
```

3. Open your web browser and navigate to `http://localhost:5001`

4. Set your desired parameters

5. Click "Run Backtest" to execute the strategy

6. View results
   
7. Download trade log as CSV for further analysis
