# app.py
from flask import Flask, request, jsonify, render_template, send_file
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

def make_commission_func(commission_per_share):
    def cost(size, price):
        return abs(size) * commission_per_share
    
    return cost



@app.route('/')
def index():
    """Renders the main HTML page."""
    return render_template('index.html')

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
        slippage_bps              = float(request.form.get('slippage_bps', 5.0))
        commission_func = make_commission_func(per_share_commission_rate)
        spread_fraction = slippage_bps / 10_000.0      

        # --- Run the backtest ---
        bt = Backtest(df_strategy, OpeningRangeBreakout, 
                      cash=cash, 
                      commission=commission_func, 
                      spread=spread_fraction,
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
