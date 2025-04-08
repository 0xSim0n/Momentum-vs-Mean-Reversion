import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def backtest_strategy(prices, z_threshold=1.0, mom_threshold=0.02, show_plot=True):
    df = prices.copy().to_frame(name='Price')
    df['SMA_10'] = df['Price'].rolling(10).mean()
    df['STD_10'] = df['Price'].rolling(10).std()
    df['Z_score'] = (df['Price'] - df['SMA_10']) / df['STD_10']
    df['Momentum'] = df['Price'].pct_change(5)
    df['SMA_200'] = df['Price'].rolling(200).mean()

    df['MR_signal'] = 0
    df.loc[(df['Z_score'] < -z_threshold) & (df['Price'] < df['SMA_200']), 'MR_signal'] = 1
    df.loc[(df['Z_score'] > z_threshold) & (df['Price'] > df['SMA_200']), 'MR_signal'] = -1

    df['MOM_signal'] = 0
    df.loc[df['Momentum'] > mom_threshold, 'MOM_signal'] = 1
    df.loc[df['Momentum'] < -mom_threshold, 'MOM_signal'] = -1

    df['MR_position'] = df['MR_signal'].replace(to_replace=0, method='ffill').fillna(0)
    df['MOM_position'] = df['MOM_signal'].replace(to_replace=0, method='ffill').fillna(0)

    df['Return'] = df['Price'].pct_change().shift(-1)
    df['MR_return'] = df['MR_position'] * df['Return']
    df['MOM_return'] = df['MOM_position'] * df['Return']

    df['MR_equity'] = (1 + df['MR_return'].fillna(0)).cumprod()
    df['MOM_equity'] = (1 + df['MOM_return'].fillna(0)).cumprod()

    df['BuyHold'] = (1 + df['Return'].fillna(0)).cumprod()

    def strategy_metrics(returns):
        sharpe = returns.mean() / returns.std() * np.sqrt(252)
        drawdown = (1 + returns.fillna(0)).cumprod().cummax() - (1 + returns.fillna(0)).cumprod()
        max_dd = drawdown.max()
        hit_ratio = (returns > 0).sum() / returns.count()
        return round(sharpe, 2), round(max_dd, 2), round(hit_ratio, 2)

    def buy_hold_metrics(series):
        returns = series.pct_change().shift(-1)
        sharpe = returns.mean() / returns.std() * np.sqrt(252)
        drawdown = (1 + returns.fillna(0)).cumprod().cummax() - (1 + returns.fillna(0)).cumprod()
        max_dd = drawdown.max()
        hit_ratio = (returns > 0).sum() / returns.count()
        return round(sharpe, 2), round(max_dd, 2), round(hit_ratio, 2)

    mr_metrics = strategy_metrics(df['MR_return'])
    mom_metrics = strategy_metrics(df['MOM_return'])
    bh_metrics = buy_hold_metrics(df['Price'])

    mr_trades = df['MR_position'].diff().abs() > 0
    num_mr_trades = mr_trades.sum()
    avg_mr_profit = df['MR_return'][mr_trades].mean()

    mom_trades = df['MOM_position'].diff().abs() > 0
    num_mom_trades = mom_trades.sum()
    avg_mom_profit = df['MOM_return'][mom_trades].mean()

    if show_plot:
        plt.figure(figsize=(10, 5))
        df['MR_equity'].plot(label='Mean Reversion')
        df['MOM_equity'].plot(label='Momentum')
        df['BuyHold'].plot(label='Buy & Hold')
        plt.title('Equity Curve: Mean Reversion vs Momentum vs Buy & Hold')
        plt.legend()
        plt.grid(True)
        plt.show()

    metrics_df = pd.DataFrame({
        'Strategy': ['Mean Reversion', 'Momentum', 'Buy & Hold'],
        'Sharpe': [mr_metrics[0], mom_metrics[0], bh_metrics[0]],
        'Max Drawdown': [mr_metrics[1], mom_metrics[1], bh_metrics[1]],
        'Hit Ratio': [mr_metrics[2], mom_metrics[2], bh_metrics[2]],
        'Trades': [num_mr_trades, num_mom_trades, '-'],
        'Avg Profit/Trade': [round(avg_mr_profit, 4), round(avg_mom_profit, 4), '-']
    })

    return metrics_df, df

tickers = ["SPY", "AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"]

raw_data = yf.download(tickers, start="2019-01-01", end="2024-12-31")
data = raw_data['Close']

price_series = data['SPY'].dropna()
metrics, df = backtest_strategy(price_series, z_threshold=1.0, mom_threshold=0.02, show_plot=True)

print(metrics)