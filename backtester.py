# my_trading_bot/backtester.py
import pandas as pd
import numpy as np
from strategy import TradingStrategy
from risk_manager import RiskManager
from config import load_config
from logger import setup_logging
import asyncio

class Backtester:
    def __init__(self, config, logger, strategy_class=TradingStrategy, risk_manager_class=RiskManager):
        self.config = config
        self.logger = logger
        self.strategy = strategy_class(config, logger)
        self.risk_manager = risk_manager_class(config, logger)
        self.logger.info("Backtester initialized with advanced metrics.")
        
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
        self.risk_manager.current_capital = self.config["INITIAL_CAPITAL"]
        self.risk_manager.reset_daily_metrics()

        for i in range(len(historical_data)):
            current_candle = historical_data.iloc[i:i+1]
            current_time = historical_data.index[i]
            
            # Simulate daily reset for daily loss limit
            if i > 0 and (historical_data.index[i].day != historical_data.index[i-1].day):
                 self.risk_manager.reset_daily_metrics()

            # If we have an open position, check for stop-loss or take-profit
            position_closed_this_candle = False
            if self.open_position:
                low_price = current_candle['low'].iloc[-1]
                high_price = current_candle['high'].iloc[-1]
                
                if low_price <= self.open_position['stop_loss']:
                    self._close_position(self.open_position['stop_loss'], "STOP_LOSS", current_time)
                    position_closed_this_candle = True
                elif high_price >= self.open_position['take_profit']:
                    self._close_position(self.open_position['take_profit'], "TAKE_PROFIT", current_time)
                    position_closed_this_candle = True
            
            # Generate signal based on current historical data up to this point
            if not position_closed_this_candle:
                signal = self.strategy.generate_signal(historical_data.iloc[:i+1])
                
                if signal["action"] == "BUY" and not self.open_position:
                    approved_order = self.risk_manager.evaluate_signal(signal, current_candle['close'].iloc[-1])
                    if approved_order:
                        self._open_position(approved_order, current_candle['close'].iloc[-1], current_time)
                elif signal["action"] == "SELL" and self.open_position:
                    self._close_position(current_candle['close'].iloc[-1], "STRATEGY_SELL", current_time)

            # CALCULAR O PATRIMÓNIO LÍQUIDO REAL (EQUITY) NA VELA CORRENTE
            if self.open_position:
                current_equity = self.current_capital + (self.open_position['quantity'] * current_candle['close'].iloc[-1])
            else:
                current_equity = self.current_capital
            
            if i == 0:
                self.capital_history = [current_equity]
            else:
                self.capital_history.append(current_equity)

        # Se no fim do backtest ainda houver uma posição aberta, fechamo-la virtualmente para contabilidade exata
        if self.open_position:
            last_close = historical_data['close'].iloc[-1]
            last_time = historical_data.index[-1]
            self._close_position(last_close, "MARKET_CLOSE_END", last_time)
            self.capital_history[-1] = self.current_capital

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
        self.current_capital -= (entry_price * order_details["quantity"])
        self.logger.info(f"[{timestamp}] Opened position: {self.open_position}")

    def _close_position(self, exit_price, reason, timestamp):
        if not self.open_position:
            self.logger.warning("Attempted to close a position that was not open.")
            return

        pnl = (exit_price - self.open_position["entry_price"]) * self.open_position["quantity"]
        self.current_capital += (exit_price * self.open_position["quantity"])
        
        self.risk_manager.update_profit_loss(pnl)
        
        closed_trade = {
            "entry_timestamp": self.open_position["entry_timestamp"],
            "exit_timestamp": timestamp,
            "action": self.open_position["action"],
            "symbol": self.open_position["symbol"],
            "entry_price": self.open_position["entry_price"],
            "exit_price": exit_price,
            "quantity": self.open_position["quantity"],
            "position_value": self.open_position["entry_price"] * self.open_position["quantity"], # Valor investido
            "pnl": pnl,
            "pnl_pct": (exit_price - self.open_position["entry_price"]) / self.open_position["entry_price"] * 100,
            "capital_after": self.current_capital, # Saldo da banca após fecho
            "reason": reason,
            "status": "CLOSED"
        }
        self.trades.append(closed_trade)
        self.logger.info(f"[{timestamp}] Closed position: {closed_trade}")
        self.open_position = None

    def get_performance_metrics(self):
        initial_capital = self.config["INITIAL_CAPITAL"]
        final_capital = self.current_capital
        total_pnl = final_capital - initial_capital
        total_return_pct = (total_pnl / initial_capital) * 100

        num_trades = len(self.trades)
        num_wins = sum(1 for t in self.trades if t["pnl"] > 0)
        num_losses = sum(1 for t in self.trades if t["pnl"] < 0)
        win_rate = num_wins / num_trades if num_trades > 0 else 0.0

        # Profit Factor
        gross_profits = sum(t["pnl"] for t in self.trades if t["pnl"] > 0)
        gross_losses = abs(sum(t["pnl"] for t in self.trades if t["pnl"] < 0))
        profit_factor = gross_profits / gross_losses if gross_losses > 0 else (gross_profits if gross_profits > 0 else 1.0)

        # Sharpe Ratio e Maximum Drawdown
        capital_series = pd.Series(self.capital_history)
        
        # Drawdown
        cum_max = capital_series.cummax()
        drawdowns = (capital_series - cum_max) / cum_max
        max_drawdown_pct = drawdowns.min() * 100

        # Sharpe Ratio (diário simplificado)
        daily_returns = capital_series.pct_change().dropna()
        if len(daily_returns) > 1 and daily_returns.std() != 0:
            sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365)
            sortino_downside = daily_returns[daily_returns < 0].std()
            sortino_ratio = (daily_returns.mean() / sortino_downside) * np.sqrt(365) if sortino_downside > 0 else sharpe_ratio
        else:
            sharpe_ratio = 0.0
            sortino_ratio = 0.0

        metrics = {
            "initial_capital": initial_capital,
            "final_capital": final_capital,
            "total_pnl": total_pnl,
            "total_return_pct": total_return_pct,
            "num_trades": num_trades,
            "win_rate": win_rate,
            "num_wins": num_wins,
            "num_losses": num_losses,
            "profit_factor": profit_factor,
            "max_drawdown_pct": max_drawdown_pct,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "trades": self.trades
        }

        self.logger.info(f"--- RELATÓRIO DE BACKTESTING ---")
        self.logger.info(f"Retorno Total: {total_pnl:.2f} EUR ({total_return_pct:.2f}%)")
        self.logger.info(f"Total de Trades: {num_trades} | Taxa de Vitória: {win_rate*100:.1f}%")
        self.logger.info(f"Fator de Lucro: {profit_factor:.2f}")
        self.logger.info(f"Max Drawdown: {max_drawdown_pct:.2f}%")
        self.logger.info(f"Sharpe Ratio: {sharpe_ratio:.2f} | Sortino Ratio: {sortino_ratio:.2f}")
        self.logger.info(f"--------------------------------")

        return metrics

if __name__ == "__main__":
    async def test_backtester():
        config = load_config()
        logger = setup_logging()
        
        dates = pd.date_range(start="2023-01-01", periods=100, freq="1h")
        
        prices = []
        base_price = 100
        for i in range(100):
            noise = np.sin(i / 5.0) * 15 + np.sin(i / 2.0) * 5
            prices.append(base_price + i*0.5 + noise)
            
        data = {
            'open': prices,
            'high': [p + 2 for p in prices],
            'low': [p - 2 for p in prices],
            'close': prices,
            'volume': [1000] * 100
        }
        test_df = pd.DataFrame(data, index=dates)
        
        config["SHORT_WINDOW"] = 10
        config["LONG_WINDOW"] = 25
        
        backtester = Backtester(config, logger)
        trades, capital_history = await backtester.run_backtest(test_df)
        metrics = backtester.get_performance_metrics()

    asyncio.run(test_backtester())
