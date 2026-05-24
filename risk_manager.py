# my_trading_bot/risk_manager.py
class RiskManager:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.current_capital = config["INITIAL_CAPITAL"]
        self.daily_profit_loss = 0.0
        self.logger.info(f"RiskManager initialized. Capital: {self.current_capital} EUR")

    def evaluate_signal(self, signal, current_price=None):
        if signal["action"] == "HOLD":
            return None

        if current_price is None or current_price <= 0:
            self.logger.error("current_price must be a positive number for BUY/SELL signals.")
            return None

        # 1. Verificar Limite de Perda Diária
        max_daily_loss = abs(self.current_capital * (self.config["MAX_DAILY_LOSS_PERCENT"] / 100))
        if self.daily_profit_loss <= -max_daily_loss:
            self.logger.warning(
                f"Daily loss limit reached (-{max_daily_loss:.2f} EUR). "
                f"Trading suspended. Current Daily P/L: {self.daily_profit_loss:.2f} EUR"
            )
            return None

        # 2. Calcular o Stop Loss e Take Profit percentuais
        stop_loss_pct = self.config["STOP_LOSS_PERCENT"]
        take_profit_pct = self.config["TAKE_PROFIT_PERCENT"]
        
        # 3. Dimensionamento de Posição Profissional (Position Sizing)
        risk_per_trade_pct = self.config["MAX_RISK_PER_TRADE_PERCENT"]
        risk_amount = self.current_capital * (risk_per_trade_pct / 100)
        
        loss_per_unit = current_price * (stop_loss_pct / 100)
        quantity = risk_amount / loss_per_unit
        position_value = quantity * current_price
        
        # 4. Verificação de Margem e Capital Disponível (Spot trading limite)
        if position_value > self.current_capital:
            self.logger.debug(
                f"Calculated position value ({position_value:.2f} EUR) exceeds available capital ({self.current_capital:.2f} EUR). "
                f"Adjusting quantity to maximum available Spot capital."
            )
            quantity = (self.current_capital * 0.98) / current_price
            position_value = quantity * current_price

        if quantity <= 0:
            self.logger.warning(f"Calculated quantity is zero or negative. Skipping trade.")
            return None

        order_details = {
            "action": signal["action"],
            "symbol": self.config["SYMBOL"],
            "price": current_price,
            "quantity": quantity,
            "position_value": position_value,
            "stop_loss": current_price * (1 - stop_loss_pct / 100),
            "take_profit": current_price * (1 + take_profit_pct / 100),
            "risk_amount": risk_amount
        }
        
        self.logger.info(
            f"Signal APPROVED by RiskManager: {signal['action']} {quantity:.6f} {self.config['SYMBOL']} "
            f"@ {current_price:.2f} (Value: {position_value:.2f} EUR, SL: {order_details['stop_loss']:.2f}, "
            f"TP: {order_details['take_profit']:.2f}, Risked: {risk_amount:.2f} EUR)"
        )
        return order_details

    def update_profit_loss(self, realized_pnl):
        self.daily_profit_loss += realized_pnl
        self.current_capital += realized_pnl
        self.logger.info(
            f"Capital updated. Current Capital: {self.current_capital:.2f} EUR. "
            f"Daily P/L: {self.daily_profit_loss:.2f} EUR"
        )

    def reset_daily_metrics(self):
        self.daily_profit_loss = 0.0
        self.logger.info("Daily P/L metrics reset.")
