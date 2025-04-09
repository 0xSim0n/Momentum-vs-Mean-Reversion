# Momentum vs Mean Reversion: Trading Strategy Backtest

This project implements and compares three trading strategies:

- **Momentum**
- **Mean Reversion**
- **Combined (Momentum + Mean Reversion)**
- **Buy & Hold (benchmark)**

It uses historical stock data to evaluate performance and risk through backtesting in Python.

## 📊 Strategy Logic

- **Momentum**: Go long if 5-day return > 2%, short if < -2%.
- **Mean Reversion**: Go long if Z-score (10-day MA) < -1 and price < 200-day MA, short if Z-score > 1 and price > 200-day MA.
- **Combined Strategy**: Hybrid of Momentum and Mean Reversion, averaging their signals.
- **Buy & Hold**: Simply buy and hold the asset over the period.

## 🧪 Methodology

- **Data Source**: Yahoo Finance via `yfinance`
- **Assets Tested**: SPY, AAPL, MSFT, GOOGL, NVDA, AMZN
- **Backtest Period**: 2019–2024
- **Transaction Costs**: All strategies account for transaction costs (default: 0.1% per trade), applied whenever the position changes. This ensures more realistic performance estimates.
- **Evaluation Metrics**:
  - Sharpe Ratio
  - Sortino Ratio
  - Volatility
  - CAGR (Compound Annual Growth Rate)
  - Max Drawdown
  - Hit Ratio (win rate)
  - Number of Trades
  - Average Profit per Trade
  - Equity Curve Plot

## 📁 Project Structure

```
├── main.py       
├── README.md                    
└── example_output.png
```

## 📈 Example Output

Initial test on SPY comparing Momentum and simple Z-score-based Mean Reversion (no SMA 200 filter).

![Equity Curve Example](example_output.png)

In the next test, we applied a 200-day moving average filter to the Mean Reversion strategy to avoid counter-trend trades.

![Equity Curve Example  2](output_2.png)

Finally, we added a Buy & Hold benchmark to compare how a passive investment approach would have performed over the same period.

![Equity Curve Example  3](output_3.png)

## 🔧 Requirements

- Python 3.x
- pandas
- numpy
- matplotlib
- yfinance

Install all dependencies with:

```bash
pip install pandas numpy matplotlib yfinance
```

## 📃 License
MIT License