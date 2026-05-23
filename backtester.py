# my_trading_bot/backtester.py
# This module will be developed later for backtesting the strategy
import pandas as pd
from OlimpoTrade.strategy import TradingStrategy
from my_trading_bot.risk_manager import RiskManager
from my_trading_bot.config import load_config
from my_trading_bot.logger import setup_logging
import asyncio # Import asyncio for async operations if needed in tests

class Backtester:
    def __init__(self, config, logger, strategy_class=TradingStrategy, risk_manager_class=RiskManager):
        self.config = config
        self.logger = logger
        self.strategy = strategy_class(config, logger)
        self.risk_manager = risk_manager_class(config, logger)
        self.logger.info("Backtester initialized.")
        
        self.trades = []
        self.capital_history = [config["INITIAL_CAPITAL"]]
        self.current_capital = config["INITIAL_CAPITAL"]
        self.open_position = None

    async def run_backtest(self, historical_data):
        self.logger.info("Starting backtest...")
        
        # Reset for each run
        self.trades = []
        self.capital_history = [self.config["INITIAL_CAPITAL"]]
        self.current_capital = self.config["INITIAL_CAPITAL"]
        self.open_position = None
        self.risk_manager.current_capital = self.config["INITIAL_CAPITAL"] # Ensure risk manager has correct capital
        self.risk_manager.reset_daily_metrics() # Reset daily P/L

        for i in range(len(historical_data)):
            current_candle = historical_data.iloc[i:i+1] # Pass a single candle as a DataFrame
            
            # Simulate daily reset for daily loss limit
            # This logic needs to be more robust for actual day changes
            # For simplicity, we'll assume a new 'day' after a certain number of candles
            if i > 0 and (historical_data.index[i].day != historical_data.index[i-1].day):
                 self.risk_manager.reset_daily_metrics()


            # If we have an open position, check for stop-loss or take-profit
            if self.open_position:
                if current_candle['low'].iloc[-1] <= self.open_position['stop_loss']:
                    self._close_position(current_candle['low'].iloc[-1], "STOP_LOSS")
                    continue
                elif current_candle['high'].iloc[-1] >= self.open_position['take_profit']:
                    self._close_position(current_candle['high'].iloc[-1], "TAKE_PROFIT")
                    continue
            
            # Generate signal based on current historical data up to this point
            # The strategy should work on a slice of data up to the current point
            signal = self.strategy.generate_signal(historical_data.iloc[:i+1])
            
            if signal["action"] == "BUY" and not self.open_position:
                approved_order = self.risk_manager.evaluate_signal(signal, current_candle['close'].iloc[-1])
                if approved_order:
                    self._open_position(approved_order, current_candle['close'].iloc[-1], current_candle.index[-1])
            elif signal["action"] == "SELL" and self.open_position:
                # In a simple long-only bot, SELL means close position
                self._close_position(current_candle['close'].iloc[-1], "STRATEGY_SELL")

            self.capital_history.append(self.current_capital)

        self.logger.info("Backtest finished.")
        return self.trades, self.capital_history

    def _open_position(self, order_details, entry_price, timestamp):
        self.open_position = {
            "entry_timestamp": timestamp,
            "action": order_details["action"],
            "symbol": order_details["symbol"],
            "entry_price": entry_price,
            "quantity": order_details["quantity"],
            "stop_loss": order_details["stop_loss"],
            "take_profit": order_details["take_profit"],
            "status": "OPEN"
        }
        self.current_capital -= (entry_price * order_details["quantity"]) # Deduct from capital
        self.logger.info(f"Opened position: {self.open_position}")

    def _close_position(self, exit_price, reason):
        if not self.open_position:
            self.logger.warning("Attempted to close a position that was not open.")
            return

        pnl = (exit_price - self.open_position["entry_price"]) * self.open_position["quantity"]
        self.current_capital += (exit_price * self.open_position["quantity"]) # Add back to capital
        
        self.risk_manager.update_profit_loss(pnl) # Update risk manager's P/L
        
        closed_trade = {
            "entry_timestamp": self.open_position["entry_timestamp"],
            "exit_timestamp": pd.Timestamp.now(), # In a real backtest, this would be current candle's timestamp
            "action": self.open_position["action"],
            "symbol": self.open_position["symbol"],
            "entry_price": self.open_position["entry_price"],
            "exit_price": exit_price,
            "quantity": self.open_position["quantity"],
            "pnl": pnl,
            "reason": reason,
            "status": "CLOSED"
        }
        self.trades.append(closed_trade)
        self.logger.info(f"Closed position: {closed_trade}")
        self.open_position = None # Reset open position

    def get_performance_metrics(self):
        # Calculate various performance metrics like total P/L, win rate, Sharpe ratio, etc.
        total_pnl = sum(t["pnl"] for t in self.trades) if self.trades else 0.0
        num_wins = sum(1 for t in self.trades if t["pnl"] > 0)
        num_losses = sum(1 for t in self.trades if t["pnl"] < 0)
        win_rate = num_wins / len(self.trades) if self.trades else 0.0

        self.logger.info(f"Backtest Performance: Total PnL={total_pnl}, Win Rate={win_rate}")
        return {"total_pnl": total_pnl, "win_rate": win_rate, "trades": self.trades}

if __name__ == "__main__":
    async def test_backtester():
        config = load_config()
        logger = setup_logging()
        
        # Create some dummy historical data for testing
        data = {
            'timestamp': pd.to_datetime(['2023-01-01 00:00:00', '2023-01-01 01:00:00', '2023-01-01 02:00:00',
                                         '2023-01-01 03:00:00', '2023-01-01 04:00:00', '2023-01-01 05:00:00',
                                         '2023-01-01 06:00:00', '2023-01-01 07:00:00', '2023-01-01 08:00:00',
                                         '2023-01-01 09:00:00', '2023-01-01 10:00:00', '2023-01-02 00:00:00']),
            'open': [100, 102, 101, 103, 105, 104, 106, 107, 108, 109, 110, 112],
            'high': [103, 103, 102, 104, 106, 105, 107, 108, 109, 110, 111, 113],
            'low': [99, 100, 99, 100, 102, 102, 103, 104, 105, 106, 107, 109],
            'close': [102, 101, 101, 102, 104, 103, 105, 106, 107, 108, 109, 111],
            'volume': [100, 110, 90, 120, 130, 100, 110, 100, 120, 130, 140, 150]
        }
        test_df = pd.DataFrame(data).set_index('timestamp')
        
        backtester = Backtester(config, logger)
        trades, capital_history = await backtester.run_backtest(test_df)
        metrics = backtester.get_performance_metrics()
        
        print("\nTrades:")
        for trade in trades:
            print(trade)
        print(f"\nFinal Capital: {capital_history[-1]}")
        print(f"Performance Metrics: {metrics}")

    asyncio.run(test_backtester())
