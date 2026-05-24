# my_trading_bot/order_executor.py
import ccxt
import asyncio
import random
import time

class OrderExecutor:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.is_paper_trading = (
            self.config.get("API_KEY") == "mock_api_key_for_paper_trading" or
            self.config.get("ENV") == "development" or
            self.config.get("PAPER_TRADING", True)
        )
        
        if self.is_paper_trading:
            self.logger.info("OrderExecutor running in LOCAL PAPER TRADING (SIMULATION) mode.")
            self.exchange = None
        else:
            try:
                self.exchange = self._initialize_exchange()
                # Se as chaves pertencerem à testnet, ativa sandbox
                if self.config.get("USE_TESTNET", False):
                    self.exchange.set_sandbox_mode(True)
                    self.logger.info("OrderExecutor running in EXCHANGE SANDBOX (TESTNET) mode.")
                else:
                    self.logger.warning("OrderExecutor running in LIVE TRADING mode! Real funds will be used.")
            except Exception as e:
                self.logger.error(f"Failed to initialize exchange connection: {e}. Falling back to LOCAL PAPER TRADING.")
                self.is_paper_trading = True
                self.exchange = None

    def _initialize_exchange(self):
        exchange_class = getattr(ccxt, self.config["EXCHANGE_NAME"])
        return exchange_class({
            'apiKey': self.config["API_KEY"],
            'secret': self.config["API_SECRET"],
            'enableRateLimit': True,
        })

    async def place_order(self, order_details):
        action = order_details["action"]
        symbol = order_details["symbol"]
        quantity = order_details["quantity"]
        price = order_details["price"]
        stop_loss = order_details.get("stop_loss")
        take_profit = order_details.get("take_profit")

        self.logger.info(f"Preparing to place {action} order for {quantity:.6f} {symbol} @ {price:.2f}")

        # Se for Paper Trading local (Simulado)
        if self.is_paper_trading:
            await asyncio.sleep(0.5) # Simular latência de rede
            mock_order_id = f"mock-order-{int(time.time())}-{random.randint(1000, 9999)}"
            mock_order = {
                'id': mock_order_id,
                'symbol': symbol,
                'type': 'market',
                'side': action.lower(),
                'price': price,
                'amount': quantity,
                'cost': quantity * price,
                'filled': quantity,
                'remaining': 0.0,
                'status': 'closed',
                'fee': {'cost': quantity * price * 0.001, 'currency': 'USDT'}, # 0.1% de taxa simulada
                'info': {'message': 'Simulated Paper Trading Order'}
            }
            self.logger.info(
                f"[SIMULATION] Order PLACED successfully. ID: {mock_order_id}. "
                f"Value: {mock_order['cost']:.2f} USDT, Fee: {mock_order['fee']['cost']:.4f} USDT"
            )
            if stop_loss:
                self.logger.info(f"[SIMULATION] Simulated SL trigger set at {stop_loss:.2f}")
            if take_profit:
                self.logger.info(f"[SIMULATION] Simulated TP trigger set at {take_profit:.2f}")
            return mock_order

        # Se for Live Trading ou Testnet Real via API
        try:
            order = None
            if action == "BUY":
                order = await self.exchange.create_market_buy_order(symbol, quantity)
            elif action == "SELL":
                order = await self.exchange.create_market_sell_order(symbol, quantity)
            
            self.logger.info(f"Exchange order placed successfully: {order}")

            if stop_loss:
                self.logger.info(f"Stop-loss is configured at {stop_loss:.2f}. Place stop-loss order if supported on spot account.")
            if take_profit:
                self.logger.info(f"Take-profit is configured at {take_profit:.2f}. Place limit take-profit order if supported.")

            return order

        except ccxt.InsufficientFunds as e:
            self.logger.error(f"Insufficient funds to place order: {e}")
            return None
        except ccxt.NetworkError as e:
            self.logger.error(f"Network error while placing order: {e}. Retrying in 2 seconds...")
            await asyncio.sleep(2.0)
            try:
                # Tentativa de retry
                if action == "BUY":
                    order = await self.exchange.create_market_buy_order(symbol, quantity)
                elif action == "SELL":
                    order = await self.exchange.create_market_sell_order(symbol, quantity)
                return order
            except Exception as retry_err:
                self.logger.error(f"Retry failed: {retry_err}")
                return None
        except ccxt.ExchangeError as e:
            self.logger.error(f"Exchange error while placing order: {e}")
            return None
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in order_executor: {e}", exc_info=True)
            return None
