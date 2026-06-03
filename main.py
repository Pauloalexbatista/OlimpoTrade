# my_trading_bot/main.py
import asyncio
from logger import setup_logging
from config import load_config
from data_collector import DataCollector
from strategy import StrategyFactory
from risk_manager import RiskManager
from order_executor import OrderExecutor

async def main():
    config = load_config()
    logger = setup_logging()

    logger.info("Bot started...")

    # Initialize components
    data_collector = DataCollector(config, logger)
    strategy = StrategyFactory.get_strategy(config, logger)
    risk_manager = RiskManager(config, logger)
    order_executor = OrderExecutor(config, logger)

    # Main trading loop
    while True:
        try:
            # 1. Collect data
            current_data = await data_collector.get_latest_data()
            if current_data is None or current_data.empty:
                logger.warning("No data collected, skipping this cycle.")
                await asyncio.sleep(config.get("TRADING_INTERVAL_SECONDS", 300))
                continue

            # 2. Generate signal
            signal = strategy.generate_signal(current_data)
            logger.info(f"Signal generated: {signal.get('message', 'No message')}")

            # 3. Apply risk management
            if signal and signal["action"] != "HOLD":
                approved_order = risk_manager.evaluate_signal(signal, signal.get("price"))
                if approved_order:
                    logger.info(f"Order approved by risk manager: {approved_order}")
                    await order_executor.place_order(approved_order)
                else:
                    logger.warning("Order rejected by risk manager")

            logger.info("Trading cycle completed successfully.")

        except Exception as e:
            logger.error(f"An error occurred in main loop: {e}", exc_info=True)

        await asyncio.sleep(config.get("TRADING_INTERVAL_SECONDS", 300))

if __name__ == "__main__":
    asyncio.run(main())
