import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from itertools import product

def backtest_strategy(prices, volume, z_threshold=1.5, mom_threshold=0.05, transaction_cost=0.001, show_plot=True):
    df = prices.copy().to_frame(name='Price')
    df['Volume'] = volume

    df['SMA_20'] = df['Price'].rolling(20).mean()
    df['STD_20'] = df['Price'].rolling(20).std()
    df['Z_score'] = (df['Price'] - df['SMA_20']) / df['STD_20']
    df['SMA_200'] = df['Price'].rolling(200).mean()
    df['Momentum'] = df['Price'].pct_change(20)
    df['ATR'] = df['Price'].rolling(14).apply(lambda x: np.mean(np.abs(np.diff(x))), raw=True)
    df['ATR_mean'] = df['ATR'].rolling(50).mean()
    ema12 = df['Price'].ewm(span=12, adjust=False).mean()
    ema26 = df['Price'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    delta = df['Price'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    df['Volume_mean'] = df['Volume'].rolling(20).mean()
    df['Volume_filter'] = df['Volume'] > df['Volume_mean']

    df['MR_signal'] = 0
    df.loc[
        (df['Z_score'] < -z_threshold) &
        (df['Price'] < df['SMA_200']) &
        (df['ATR'] > df['ATR_mean']) &
        (df['RSI'] < 30) &
        (df['Volume_filter']), 'MR_signal'] = 1
    df.loc[
        (df['Z_score'] > z_threshold) &
        (df['Price'] > df['SMA_200']) &
        (df['ATR'] > df['ATR_mean']) &
        (df['RSI'] > 70) &
        (df['Volume_filter']), 'MR_signal'] = -1

    df['MOM_signal'] = 0
    df.loc[
        (df['Momentum'] > mom_threshold) &
        (df['Price'] > df['SMA_200']) &
        (df['MACD'] > df['Signal_Line']) &
        (df['RSI'] > 50) &
        (df['Volume_filter']), 'MOM_signal'] = 1
    df.loc[
        (df['Momentum'] < -mom_threshold) &
        (df['Price'] < df['SMA_200']) &
        (df['MACD'] < df['Signal_Line']) &
        (df['RSI'] < 50) &
        (df['Volume_filter']), 'MOM_signal'] = -1

    df['MR_position'] = df['MR_signal'].replace(0, np.nan).ffill().fillna(0)
    df['MOM_position'] = df['MOM_signal'].replace(0, np.nan).ffill().fillna(0)
    df['COMB_position'] = ((df['MR_position'] + df['MOM_position']) / 2).round()

    df['Return'] = df['Price'].pct_change().shift(-1)
    for strat in ['MR', 'MOM', 'COMB']:
        df[f'{strat}_change'] = df[f'{strat}_position'].diff().abs()
        df[f'{strat}_cost'] = df[f'{strat}_change'] * transaction_cost
        df[f'{strat}_return'] = df[f'{strat}_position'] * df['Return']
        df[f'{strat}_return_net'] = df[f'{strat}_return'] - df[f'{strat}_cost']
        df[f'{strat}_equity'] = (1 + df[f'{strat}_return_net'].fillna(0)).cumprod()

    df['BuyHold'] = (1 + df['Return'].fillna(0)).cumprod()

    def strategy_metrics(returns):
        returns = returns.dropna()
        sharpe = returns.mean() / returns.std() * np.sqrt(252)
        sortino = returns.mean() / returns[returns < 0].std() * np.sqrt(252)
        volatility = returns.std() * np.sqrt(252)
        cagr = (1 + returns).prod() ** (252 / len(returns)) - 1
        drawdown = (1 + returns).cumprod().cummax() - (1 + returns).cumprod()
        max_dd = drawdown.max()
        hit_ratio = (returns > 0).sum() / len(returns)
        return {
            'Sharpe': round(sharpe, 2),
            'Sortino': round(sortino, 2),
            'Volatility': round(volatility, 2),
            'CAGR': round(cagr, 2),
            'Max Drawdown': round(max_dd, 2),
            'Hit Ratio': round(hit_ratio, 2)
        }

    def buy_hold_metrics(series):
        returns = series.pct_change().shift(-1).dropna()
        return strategy_metrics(returns)

    mr_metrics = strategy_metrics(df['MR_return_net'])
    mom_metrics = strategy_metrics(df['MOM_return_net'])
    comb_metrics = strategy_metrics(df['COMB_return_net'])
    bh_metrics = buy_hold_metrics(df['Price'])

    mr_trades = df['MR_position'].diff().abs() > 0
    mom_trades = df['MOM_position'].diff().abs() > 0
    comb_trades = df['COMB_position'].diff().abs() > 0

    metrics_df = pd.DataFrame([
        {'Strategy': 'Mean Reversion', **mr_metrics,
         'Trades': mr_trades.sum(), 'Avg Profit/Trade': round(df['MR_return_net'][mr_trades].mean(), 4)},
        {'Strategy': 'Momentum', **mom_metrics,
         'Trades': mom_trades.sum(), 'Avg Profit/Trade': round(df['MOM_return_net'][mom_trades].mean(), 4)},
        {'Strategy': 'Combined', **comb_metrics,
         'Trades': comb_trades.sum(), 'Avg Profit/Trade': round(df['COMB_return_net'][comb_trades].mean(), 4)},
        {'Strategy': 'Buy & Hold', **bh_metrics,
         'Trades': '-', 'Avg Profit/Trade': '-'}
    ])

    if show_plot:
        plt.figure(figsize=(10, 6))
        df['MR_equity'].plot(label='Mean Reversion')
        df['MOM_equity'].plot(label='Momentum')
        df['COMB_equity'].plot(label='Combined Strategy')
        df['BuyHold'].plot(label='Buy & Hold')
        plt.title('Equity Curve: MR vs MOM vs Combined vs Buy & Hold')
        plt.legend()
        plt.grid(True)
        plt.show()

    return metrics_df, df

def save_best_strategies(input_file='parameter_grid_search_results.csv', output_file='best_strategies_all.csv'):
    df = pd.read_csv(input_file)
    
    df['Sharpe'] = pd.to_numeric(df['Sharpe'], errors='coerce')
    df = df.dropna(subset=['Sharpe'])

    best_strategies = df.loc[df.groupby('Ticker')['Sharpe'].idxmax().values]
    best_strategies.to_csv(output_file, index=False)

    print(f"The best strategies were saved to a file: {output_file}")

TICKERS = {
    "small": ["PLUG", "FUBO", "RIOT", "SOFI", "BCLI", "SNDL", "MARA", "LUMN", "OPK"],
    "mid": ["FSLR", "ALB", "ENPH", "CHWY", "PTON", "ROKU", "LVS", "U", "RUN", "DOCN"],
    "large": ["SPY", "AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"]
}

tickers = TICKERS["small"] + TICKERS["mid"] + TICKERS["large"]
raw_data = yf.download(tickers, start="2019-01-01", end="2024-12-31")
data = raw_data['Close']
volume = raw_data['Volume']

z_threshold_values = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
mom_threshold_values = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04]
transaction_cost_values = [0.0001, 0.0005, 0.001, 0.002]

grid_results = []

for z_val, mom_val, cost_val in product(z_threshold_values, mom_threshold_values, transaction_cost_values):
    for ticker in tickers:
        price_series = data[ticker].dropna()
        volume_series = volume[ticker].dropna()
        if len(price_series) < 210:
            continue
        try:
            metrics, _ = backtest_strategy(price_series, volume_series, z_threshold=z_val, mom_threshold=mom_val, transaction_cost=cost_val, show_plot=False)
            metrics['Ticker'] = ticker
            metrics['Z_threshold'] = z_val
            metrics['MOM_threshold'] = mom_val
            metrics['Transaction_cost'] = cost_val
            grid_results.append(metrics)
        except Exception as e:
            print(f"Error for {ticker} with z={z_val}, mom={mom_val}, cost={cost_val}: {e}")

grid_results_df = pd.concat(grid_results, ignore_index=True)
grid_results_df.to_csv("parameter_grid_search_results.csv", index=False)
print("Parameter search results saved to parameter_grid_search_results.csv")

save_best_strategies()