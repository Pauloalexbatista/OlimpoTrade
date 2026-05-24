import pandas as pd
import ta

class TradingStrategy:
    def __init__(self, config=None, logger=None, short_window=20, long_window=50):
        if isinstance(config, dict):
            self.short_window = config.get("SHORT_WINDOW", short_window)
            self.long_window = config.get("LONG_WINDOW", long_window)
        else:
            self.short_window = short_window
            self.long_window = long_window
        self.logger = logger
        if self.logger:
            self.logger.info(f"Estratégia de Médias Móveis inicializada com janelas: Curta={self.short_window}, Longa={self.long_window}")
        else:
            print(f"Estratégia de Médias Móveis inicializada com janelas: Curta={self.short_window}, Longa={self.long_window}")

    def generate_signal(self, ohlcv_data: pd.DataFrame) -> dict:
        """
        Gera um sinal de compra/venda com base na estratégia de cruzamento de médias móveis.
        :param ohlcv_data: DataFrame com dados OHLCV (open, high, low, close, volume).
                           Deve conter uma coluna 'close'.
        :return: Um dicionário com 'signal' ('BUY', 'SELL', 'HOLD') e 'price' (preço de fechamento mais recente).
        """
        if ohlcv_data.empty or len(ohlcv_data) < max(self.short_window, self.long_window):
            # Não há dados suficientes para calcular as médias móveis
            return {"action": "HOLD", "signal": "HOLD", "price": None, "message": "Dados insuficientes para calcular médias móveis."}

        # Criar uma cópia para evitar SettingWithCopyWarning do Pandas
        df = ohlcv_data.copy()

        # Calcular Médias Móveis Simples (SMA)
        df['SMA_Short'] = ta.trend.sma_indicator(df['close'], window=self.short_window)
        df['SMA_Long'] = ta.trend.sma_indicator(df['close'], window=self.long_window)

        # Remover linhas com valores NaN resultantes do cálculo das médias móveis
        df = df.dropna(subset=['SMA_Short', 'SMA_Long'])

        if df.empty:
            return {"action": "HOLD", "signal": "HOLD", "price": None, "message": "Dados insuficientes após cálculo de médias móveis."}

        last_row = df.iloc[-1]
        previous_row = df.iloc[-2] if len(df) >= 2 else None

        current_price = last_row['close']
        current_sma_short = last_row['SMA_Short']
        current_sma_long = last_row['SMA_Long']

        signal = "HOLD"
        message = "Nenhum sinal claro."

        if previous_row is not None:
            previous_sma_short = previous_row['SMA_Short']
            previous_sma_long = previous_row['SMA_Long']

            # Sinal de Compra: SMA Curta cruza acima da SMA Longa
            if previous_sma_short <= previous_sma_long and current_sma_short > current_sma_long:
                signal = "BUY"
                message = "Sinal de COMPRA: SMA Curta cruzou acima da SMA Longa."
            # Sinal de Venda: SMA Curta cruza abaixo da SMA Longa
            elif previous_sma_short >= previous_sma_long and current_sma_short < current_sma_long:
                signal = "SELL"
                message = "Sinal de VENDA: SMA Curta cruzou abaixo da SMA Longa."

        return {"action": signal, "signal": signal, "price": current_price, "message": message}

if __name__ == "__main__":
    print("Testando a Estratégia de Médias Móveis...")

    # Criar dados OHLCV de exemplo
    data = {
        'close': [10, 11, 12, 11, 10, 9, 10, 11, 12, 13, 14, 13, 12, 11, 10, 9, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 2, 3]
    }
    df = pd.DataFrame(data)

    strategy = TradingStrategy(short_window=3, long_window=7)
    signal = strategy.generate_signal(df)
    print(f"Sinal Gerado: {signal}")

    df_small = pd.DataFrame({'close': [1, 2, 3, 4]})
    signal_small = strategy.generate_signal(df_small)
    print(f"Sinal Gerado (dados insuficientes): {signal_small}")
