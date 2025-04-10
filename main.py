import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def backtest_strategy(prices, z_threshold=1.0, mom_threshold=0.02,  transaction_cost=0.001, show_plot=True):
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
    df['COMB_position'] = ((df['MR_position'] + df['MOM_position']) / 2).round()

    df['Return'] = df['Price'].pct_change().shift(-1)
    df['MR_change'] = df['MR_position'].diff().abs()
    df['MOM_change'] = df['MOM_position'].diff().abs()
    df['COMB_change'] = df['COMB_position'].diff().abs()

    df['MR_cost'] = df['MR_change'] * transaction_cost
    df['MOM_cost'] = df['MOM_change'] * transaction_cost
    df['COMB_cost'] = df['COMB_change'] * transaction_cost

    df['MR_return'] = df['MR_position'] * df['Return']
    df['MOM_return'] = df['MOM_position'] * df['Return']
    df['COMB_return'] = df['COMB_position'] * df['Return']

    df['MR_return_net'] = df['MR_return'] - df['MR_cost']
    df['MOM_return_net'] = df['MOM_return'] - df['MOM_cost']
    df['COMB_return_net'] = df['COMB_return'] - df['COMB_cost']

    df['MR_equity'] = (1 + df['MR_return_net'].fillna(0)).cumprod()
    df['MOM_equity'] = (1 + df['MOM_return_net'].fillna(0)).cumprod()
    df['COMB_equity'] = (1 + df['COMB_return_net'].fillna(0)).cumprod()
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

    mr_metrics = strategy_metrics(df['MR_return'])
    mom_metrics = strategy_metrics(df['MOM_return'])
    comb_metrics = strategy_metrics(df['COMB_return'])
    bh_metrics = buy_hold_metrics(df['Price'])

    mr_trades = df['MR_position'].diff().abs() > 0
    mom_trades = df['MOM_position'].diff().abs() > 0
    comb_trades = df['COMB_position'].diff().abs() > 0

    metrics_df = pd.DataFrame([
        {'Strategy': 'Mean Reversion', **mr_metrics,
        'Trades': mr_trades.sum(), 'Avg Profit/Trade': round(df['MR_return'][mr_trades].mean(), 4)},
        {'Strategy': 'Momentum', **mom_metrics,
        'Trades': mom_trades.sum(), 'Avg Profit/Trade': round(df['MOM_return'][mom_trades].mean(), 4)},
        {'Strategy': 'Combined', **comb_metrics,
        'Trades': comb_trades.sum(), 'Avg Profit/Trade': round(df['COMB_return'][comb_trades].mean(), 4)},
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

tickers = ["SPY", "AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"]

raw_data = yf.download(tickers, start="2019-01-01", end="2024-12-31")
data = raw_data['Close']

all_metrics = []
comb_equities = {}

for ticker in tickers:
    price_series = data[ticker].dropna()
    try:
        metrics, df = backtest_strategy(price_series, z_threshold=1.0, mom_threshold=0.02, show_plot=False)
        metrics['Ticker'] = ticker
        all_metrics.append(metrics)
        comb_equities[ticker] = df['COMB_equity']
    except Exception as e:
        print(f"Error for {ticker}: {e}")

all_results_df = pd.concat(all_metrics, ignore_index=True)
all_results_df.to_csv("strategy_results.csv", index=False)
print("Results saved to strategy_results.csv")

equity_df = pd.DataFrame(comb_equities).dropna()
correlation_matrix = equity_df.corr()

plt.figure(figsize=(10, 8))
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', fmt=".2f")
plt.title("Correlation of Combined Strategy Equity Curves")
plt.show()
