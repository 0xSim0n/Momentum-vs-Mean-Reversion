import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

tickers = ["SPY", "AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"]

raw_data = yf.download(tickers, start="2019-01-01", end="2024-12-31")
data = raw_data['Close']

spy = data['SPY'].copy().to_frame()
spy['SMA_10'] = spy['SPY'].rolling(10).mean()
spy['STD_10'] = spy['SPY'].rolling(10).std()
spy['Z_score'] = (spy['SPY'] - spy['SMA_10']) / spy['STD_10']
spy['Momentum'] = spy['SPY'].pct_change(5)

spy['MR_signal'] = 0
spy.loc[spy['Z_score'] < -1, 'MR_signal'] = 1
spy.loc[spy['Z_score'] > 1, 'MR_signal'] = -1

spy['MOM_signal'] = 0
spy.loc[spy['Momentum'] > 0.02, 'MOM_signal'] = 1
spy.loc[spy['Momentum'] < -0.02, 'MOM_signal'] = -1

spy['Return'] = spy['SPY'].pct_change().shift(-1)
spy['MR_return'] = spy['MR_signal'] * spy['Return']
spy['MOM_return'] = spy['MOM_signal'] * spy['Return']

spy['MR_equity'] = (1 + spy['MR_return'].fillna(0)).cumprod()
spy['MOM_equity'] = (1 + spy['MOM_return'].fillna(0)).cumprod()

def strategy_metrics(returns):
    sharpe = returns.mean() / returns.std() * np.sqrt(252)
    drawdown = (1 + returns.fillna(0)).cumprod().cummax() - (1 + returns.fillna(0)).cumprod()
    max_dd = drawdown.max()
    hit_ratio = (returns > 0).sum() / returns.count()
    return round(sharpe, 2), round(max_dd, 2), round(hit_ratio, 2)

mr_metrics = strategy_metrics(spy['MR_return'])
mom_metrics = strategy_metrics(spy['MOM_return'])

print("Mean Reversion - Sharpe:", mr_metrics[0], "Max DD:", mr_metrics[1], "Hit ratio:", mr_metrics[2])
print("Momentum       - Sharpe:", mom_metrics[0], "Max DD:", mom_metrics[1], "Hit ratio:", mom_metrics[2])

plt.figure(figsize=(10, 5))
spy['MR_equity'].plot(label='Mean Reversion')
spy['MOM_equity'].plot(label='Momentum')
plt.title('Equity Curve: Mean Reversion vs Momentum')
plt.legend()
plt.grid(True)
plt.show()
