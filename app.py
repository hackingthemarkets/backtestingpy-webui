# app.py
from flask import Flask, request, jsonify, render_template_string, send_file
import pandas as pd
import datetime as dt
from backtesting import Backtest, Strategy
import os
import uuid
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io

# Initialize Flask App
app = Flask(__name__)
# Create a directory to store temporary files if it doesn't exist
if not os.path.exists('static'):
    os.makedirs('static')

# --- HTML & JavaScript Frontend ---
# This is the user interface for the application.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Backtesting.py Frontend</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .loader {
            border: 8px solid #f3f3f3;
            border-top: 8px solid #3498db;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            animation: spin 2s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body class="bg-gray-100 text-gray-800">

    <div class="container mx-auto p-4 md:p-8">
        <header class="text-center mb-8">
            <h1 class="text-4xl font-bold text-gray-900">Strategy Backtester</h1>
            <p class="text-lg text-gray-600 mt-2">Upload your data and configure parameters to run a backtest.</p>
        </header>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <!-- Control Panel -->
            <div class="lg:col-span-1 bg-white p-6 rounded-xl shadow-lg">
                <h2 class="text-2xl font-semibold mb-6 border-b pb-4">Configuration</h2>
                <form id="backtest-form">
                    <!-- File Upload -->
                    <div class="mb-4">
                        <label for="csv-file" class="block text-sm font-medium text-gray-700 mb-2">Upload Unadjusted Intraday Data</label>
                        <input type="file" id="csv-file" name="csv-file" accept=".csv" required
                               class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100">
                    </div>

                    <!-- Date Range -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                        <div>
                            <label for="start_date" class="block text-sm font-medium text-gray-700">Start Date (Optional)</label>
                            <input type="date" id="start_date" name="start_date" value="2016-01-01" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2">
                        </div>
                        <div>
                            <label for="end_date" class="block text-sm font-medium text-gray-700">End Date (Optional)</label>
                            <input type="date" id="end_date" name="end_date" value="2023-02-16" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2">
                        </div>
                    </div>

                    <!-- Strategy Parameters -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                        <div>
                            <label for="open_range_minutes" class="block text-sm font-medium text-gray-700">Open Range (min)</label>
                            <input type="number" id="open_range_minutes" name="open_range_minutes" value="5" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2">
                        </div>
                        <div>
                            <label for="risk_percent" class="block text-sm font-medium text-gray-700">Risk (%)</label>
                            <input type="number" id="risk_percent" name="risk_percent" value="1.0" step="0.1" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2">
                        </div>
                        <div>
                            <label for="take_profit_multiple" class="block text-sm font-medium text-gray-700">TP Multiple</label>
                            <input type="number" id="take_profit_multiple" name="take_profit_multiple" value="10" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2">
                        </div>
                        <div>
                            <label for="max_leverage" class="block text-sm font-medium text-gray-700">Max Leverage</label>
                            <input type="number" id="max_leverage" name="max_leverage" value="4" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2">
                        </div>
                         <div>
                            <label for="cash" class="block text-sm font-medium text-gray-700">Initial Cash</label>
                            <input type="number" id="cash" name="cash" value="25000" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2">
                        </div>
                        <div>
                            <label for="per_share_commission" class="block text-sm font-medium text-gray-700">Per Share Commission ($)</label>
                            <input type="number" id="per_share_commission" name="per_share_commission" value="0.0005" step="0.0001" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2">
                        </div>
                        <div>
                            <label for="slippage_cents" class="block text-sm font-medium text-gray-700">Slippage (Cents/Share)</label>
                            <input type="number" id="slippage_cents" name="slippage_cents" value="0.0" step="0.1" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2">
                        </div>
                    </div>

                    <button type="submit" class="w-full bg-blue-600 text-white font-bold py-3 px-4 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition duration-300 ease-in-out">
                        Run Backtest
                    </button>
                </form>
            </div>

            <!-- Results Display -->
            <div class="lg:col-span-2 bg-white p-6 rounded-xl shadow-lg">
                <h2 class="text-2xl font-semibold mb-6 border-b pb-4">Results</h2>
                <div id="results-container" class="text-center">
                    <div id="loader" class="loader mx-auto my-8 hidden"></div>
                    <div id="stats-container"></div>
                    <div id="export-container" class="mt-6"></div>
                    <div id="plot-container" class="mt-6"></div>
                    <div id="error-container" class="text-red-500 mt-4"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('backtest-form').addEventListener('submit', async function(e) {
            e.preventDefault();

            const form = e.target;
            const formData = new FormData(form);
            const loader = document.getElementById('loader');
            const statsContainer = document.getElementById('stats-container');
            const plotContainer = document.getElementById('plot-container');
            const errorContainer = document.getElementById('error-container');
            const exportContainer = document.getElementById('export-container');

            // Clear previous results and show loader
            statsContainer.innerHTML = '';
            plotContainer.innerHTML = '';
            errorContainer.innerHTML = '';
            exportContainer.innerHTML = '';
            loader.classList.remove('hidden');

            try {
                const response = await fetch('/run_backtest', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'An unknown error occurred.');
                }

                const data = await response.json();

                // Display Stats
                let statsHtml = '<h3 class="text-xl font-semibold mb-4">Key Statistics</h3><div class="grid grid-cols-2 md:grid-cols-3 gap-4 text-left">';
                for (const [key, value] of Object.entries(data.stats)) {
                    let formattedValue = typeof value === 'number' && !Number.isInteger(value) ? value.toFixed(2) : value;
                    statsHtml += `<div class="bg-gray-50 p-3 rounded-lg"><p class="text-sm text-gray-500">${key}</p><p class="text-lg font-medium">${formattedValue}</p></div>`;
                }
                statsHtml += '</div>';
                statsContainer.innerHTML = statsHtml;

                // Add export button if trades exist
                if (data.trade_file_id) {
                    const exportBtn = document.createElement('a');
                    exportBtn.href = `/export_trades?id=${data.trade_file_id}`;
                    exportBtn.className = 'inline-block mt-4 bg-green-600 text-white font-bold py-2 px-4 rounded-lg hover:bg-green-700 transition duration-300';
                    exportBtn.innerText = 'Export Trade Log (CSV)';
                    exportBtn.download = 'trade_log.csv';
                    exportContainer.appendChild(exportBtn);
                }

                // Display Plot or a warning if plotting failed
                if (data.plot_url) {
                    const plotUrl = data.plot_url + '?t=' + new Date().getTime(); // Cache-busting
                    plotContainer.innerHTML = `<h3 class="text-xl font-semibold my-4">Equity Curve</h3><iframe src="${plotUrl}" class="w-full h-[600px] border-0 rounded-lg shadow-md"></iframe>`;
                } else {
                    plotContainer.innerHTML = `<h3 class="text-xl font-semibold my-4">Equity Curve</h3><div class="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 rounded-lg mt-4" role="alert"><p class="font-bold">Plotting Failed</p><p>The plot could not be created. The statistics above are still valid.</p></div>`;
                }


            } catch (error) {
                console.error('Error:', error);
                errorContainer.innerText = 'Error running backtest: ' + error.message;
            } finally {
                // Hide loader
                loader.classList.add('hidden');
            }
        });
    </script>
</body>
</html>
"""

# --- Backtesting Logic ---

EARLY_CLOSE_DATES = [
    '2017-07-03 12:59:00', '2018-07-03 12:59:00', '2018-11-23 12:59:00',
    '2019-12-24 12:59:00', '2020-11-27 12:59:00', '2020-12-24 12:59:00'
]

class OpeningRangeBreakout(Strategy):
    open_range_minutes = 5
    risk_percent = 1.0
    take_profit_multiple = 10
    max_leverage = 4

    def init(self):
        self.current_day = None
        self.current_day_open = None
        self.opening_range_high = None
        self.opening_range_low = None
        self.last_minute_bar_in_opening_range = (dt.datetime(2000, 1, 1, 9, 30) + dt.timedelta(minutes=self.open_range_minutes)).time()
        self.exit_minute_bar = dt.time(15, 59)

    def _reset_range(self, day, open_price):
        self.current_day = day
        self.current_day_open = open_price
        self.opening_range_high = None
        self.opening_range_low = None

    def _get_position_size(self, entry_price: float, stop_price: float) -> int:
        per_share_risk = abs(entry_price - stop_price)
        if per_share_risk == 0: return 0
        risk_decimal = self.risk_percent / 100.0
        shares_by_risk = (risk_decimal * self.equity) / per_share_risk
        shares_by_leverage = (self.max_leverage * self.equity) / entry_price
        return int(min(shares_by_risk, shares_by_leverage))

    def next(self):
        t = self.data.index[-1]
        current_bar_date = t.date()

        if current_bar_date != self.current_day:
            self._reset_range(current_bar_date, self.data.Open[-1])

        if t.time() < self.last_minute_bar_in_opening_range:
            self.opening_range_high = max(self.opening_range_high, self.data.High[-1]) if self.opening_range_high is not None else self.data.High[-1]
            self.opening_range_low = min(self.opening_range_low, self.data.Low[-1]) if self.opening_range_low is not None else self.data.Low[-1]
            return

        if t.time() == self.last_minute_bar_in_opening_range:
            if not self.position and self.opening_range_high is not None:
                range_size = self.opening_range_high - self.opening_range_low
                if range_size == 0: return
                planned_entry_price = self.data.Close[-1]
                if self.data.Close[-1] > self.current_day_open:
                    stop_loss_price = self.opening_range_low
                    position_size = self._get_position_size(planned_entry_price, stop_loss_price)
                    take_profit_price = planned_entry_price + (self.take_profit_multiple * range_size)
                    if position_size > 0: self.buy(size=position_size, tp=take_profit_price, sl=stop_loss_price)
                elif self.data.Close[-1] < self.current_day_open:
                    stop_loss_price = self.opening_range_high
                    position_size = self._get_position_size(planned_entry_price, stop_loss_price)
                    take_profit_price = planned_entry_price - (self.take_profit_multiple * range_size)
                    if position_size > 0: self.sell(size=position_size, tp=take_profit_price, sl=stop_loss_price)

        current_bar_date_time = f"{current_bar_date} {t.time()}"
        if self.position and (t.time() == self.exit_minute_bar or current_bar_date_time in EARLY_CLOSE_DATES):
            self.position.close()

# --- Custom Plotting Function ---
def create_plotly_plot(stats, initial_cash, plot_filename, price_data=None):
    equity_curve = stats['_equity_curve']

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    
    # Plot Strategy Equity
    fig.add_trace(go.Scatter(x=equity_curve.index, y=equity_curve['Equity'], mode='lines', name='Strategy', line=dict(color='blue')), row=1, col=1)
    
    # Plot Buy & Hold Equity if data is available
    if price_data is not None and not price_data.empty:
        buy_hold_equity = (price_data['Close'] / price_data['Close'][0]) * initial_cash
        fig.add_trace(go.Scatter(x=buy_hold_equity.index, y=buy_hold_equity, mode='lines', name='Buy & Hold (Adjusted)', line=dict(color='grey', dash='dash')), row=1, col=1)
    
    # Plot Drawdown
    fig.add_trace(go.Scatter(x=equity_curve.index, y=equity_curve['DrawdownPct'] * 100, mode='lines', name='Drawdown (%)', fill='tozeroy', line=dict(color='rgba(255,0,0,0.3)')), row=2, col=1)
    
    fig.update_layout(title='Strategy Equity vs. Buy & Hold', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), height=600, margin=dict(l=50, r=50, t=80, b=50))
    fig.update_yaxes(title_text="Equity ($)", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown (%)", row=2, col=1)
    fig.write_html(plot_filename, full_html=True)

def make_commission_func(commission_per_share, slippage_cents_per_share):
    slippage_dollars_per_share = slippage_cents_per_share / 100.0

    def combined_cost(size, price):
        commission_cost = abs(size) * commission_per_share
        slippage_cost = abs(size) * slippage_dollars_per_share
        return commission_cost + slippage_cost
    return combined_cost



@app.route('/')
def index():
    """Renders the main HTML page."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/run_backtest', methods=['POST'])
def run_backtest():
    """Handles the backtest execution."""
    try:
        if 'csv-file' not in request.files: return jsonify({'error': 'No file part'}), 400
        file = request.files['csv-file']
        if file.filename == '': return jsonify({'error': 'No selected file'}), 400

        # --- Read and prepare the UNADJUSTED CSV data for the strategy ---
        df_strategy = None
        try:
            file.seek(0)
            df_temp = pd.read_csv(file, parse_dates=['caldt'], index_col='caldt')
            df_temp = df_temp.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
            df_temp.index.name = 'Date'
            df_strategy = df_temp
        except (KeyError, ValueError):
            try:
                file.seek(0)
                df_strategy = pd.read_csv(file, parse_dates=['Date'], index_col='Date')
            except Exception as e:
                 return jsonify({'error': f"Could not parse strategy CSV. Ensure it has a datetime index ('caldt' or 'Date') and OHLCV columns. Details: {e}"}), 400
        
        if df_strategy is None: return jsonify({'error': 'Failed to read strategy CSV file.'}), 400
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df_strategy.columns for col in required_cols):
             return jsonify({'error': f"Strategy CSV is missing required columns after processing. Required: {required_cols}"}), 400

        # --- Filter by Date Range ---
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        if start_date and end_date:
            df_strategy = df_strategy.loc[start_date:end_date]
        elif start_date:
            df_strategy = df_strategy.loc[start_date:]
        elif end_date:
            df_strategy = df_strategy.loc[:end_date]
        
        if df_strategy.empty:
            return jsonify({'error': 'No strategy data available for the selected date range.'}), 400
            
        # --- Load ADJUSTED data for Buy & Hold benchmark ---
        df_benchmark = None
        buy_and_hold_return = None
        adjusted_data_path = 'TQQQ_adjusted.csv'
        try:
            df_benchmark = pd.read_csv(adjusted_data_path, parse_dates=['Date'], index_col='Date')
            # Filter benchmark data to the same date range
            if start_date and end_date:
                df_benchmark = df_benchmark.loc[start_date:end_date]
            elif start_date:
                df_benchmark = df_benchmark.loc[start_date:]
            elif end_date:
                df_benchmark = df_benchmark.loc[:end_date]
            
            if not df_benchmark.empty:
                start_price = df_benchmark['Close'].iloc[0]
                end_price = df_benchmark['Close'].iloc[-1]
                buy_and_hold_return = ((end_price / start_price) - 1) * 100

        except FileNotFoundError:
            print(f"Warning: Adjusted data file not found at '{adjusted_data_path}'. Buy & Hold benchmark will not be plotted.")
        except Exception as e:
            print(f"Warning: Could not process adjusted data file. Error: {e}")


        # --- Get parameters from form ---
        params = {
            'open_range_minutes': int(request.form.get('open_range_minutes', 5)),
            'risk_percent': float(request.form.get('risk_percent', 1.0)),
            'take_profit_multiple': float(request.form.get('take_profit_multiple', 10)),
            'max_leverage': float(request.form.get('max_leverage', 4)),
        }
        cash = int(request.form.get('cash', 25000))
        per_share_commission_rate = float(request.form.get('per_share_commission', 0.0005))
        slippage_cents = float(request.form.get('slippage_cents', 1.0))
        
        commission_and_slippage_func = make_commission_func(per_share_commission_rate, slippage_cents)

        # --- Run the backtest ---
        bt = Backtest(df_strategy, OpeningRangeBreakout, 
                      cash=cash, 
                      commission=commission_and_slippage_func, 
                      margin=1./params['max_leverage'])
        stats = bt.run(**params)

        # --- Generate and save files ---
        file_id = uuid.uuid4().hex
        plot_url = None
        trade_file_id = None

        # Save plot
        try:
            plot_filename_html = f'plot_{file_id}.html'
            plot_filepath = os.path.join('static', plot_filename_html)
            create_plotly_plot(stats, cash, plot_filepath, price_data=df_benchmark)
            plot_url = f'/static/{plot_filename_html}'
        except Exception as e:
            print(f"Warning: Plot generation failed. Error: {e}")

        # Save trades
        trades_df = stats['_trades']
        if not trades_df.empty:
            trades_filepath = os.path.join('static', f'trades_{file_id}.csv')
            trades_df.to_csv(trades_filepath)
            trade_file_id = file_id

        # --- Prepare and return the results ---
        display_stats = {
            'Return [%]': stats['Return [%]'],
            'Buy & Hold Return [%]': buy_and_hold_return,
            'Sharpe Ratio': stats['Sharpe Ratio'],
            'Max. Drawdown [%]': stats['Max. Drawdown [%]'],
            'Win Rate [%]': stats['Win Rate [%]'],
            '# Trades': stats['# Trades'],
            'Avg. Trade [%]': stats['Avg. Trade [%]'],
            'Profit Factor': stats['Profit Factor'],
        }
        
        # Filter out the Buy & Hold stat if it couldn't be calculated
        display_stats = {k: v for k, v in display_stats.items() if v is not None}


        return jsonify({'stats': display_stats, 'plot_url': plot_url, 'trade_file_id': trade_file_id})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/export_trades')
def export_trades():
    """Serves the trade log CSV for download."""
    file_id = request.args.get('id')
    if not file_id:
        return "Error: No file ID provided.", 400
    
    filepath = os.path.join('static', f'trades_{file_id}.csv')
    if not os.path.exists(filepath):
        return "Error: File not found.", 404

    return send_file(filepath, as_attachment=True, download_name='trade_log.csv')


if __name__ == '__main__':
    app.run(debug=True, port=5001)
