import pandas as pd
import ta
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    @abstractmethod
    def generate_signal(self, ohlcv_data: pd.DataFrame) -> dict:
        """
        Gera um sinal de compra/venda com base na estratégia implementada.
        :param ohlcv_data: DataFrame com dados OHLCV (open, high, low, close, volume).
        :return: Dicionário com 'action' ('BUY', 'SELL', 'HOLD'), 'signal' ('BUY' | 'SELL' | 'HOLD'),
                 'price' (preço de fecho mais recente), e 'message' (detalhes do sinal).
        """
        pass

class SMACrossoverStrategy(BaseStrategy):
    """
    Estratégia clássica de cruzamento de duas Médias Móveis Simples (SMA).
    """
    def __init__(self, short_window=9, long_window=21, logger=None):
        self.short_window = short_window
        self.long_window = long_window
        self.logger = logger
        msg = f"Estratégia SMA Crossover inicializada (Curta={self.short_window}, Longa={self.long_window})"
        if self.logger:
            self.logger.info(msg)
        else:
            print(msg)

    def generate_signal(self, ohlcv_data: pd.DataFrame) -> dict:
        if ohlcv_data.empty or len(ohlcv_data) < max(self.short_window, self.long_window):
            return {"action": "HOLD", "signal": "HOLD", "price": None, "message": "Dados insuficientes para calcular médias móveis simples."}

        df = ohlcv_data.copy()
        df['SMA_Short'] = ta.trend.sma_indicator(df['close'], window=self.short_window)
        df['SMA_Long'] = ta.trend.sma_indicator(df['close'], window=self.long_window)
        df = df.dropna(subset=['SMA_Short', 'SMA_Long'])

        if df.empty:
            return {"action": "HOLD", "signal": "HOLD", "price": None, "message": "Dados insuficientes após cálculo de médias."}

        last_row = df.iloc[-1]
        previous_row = df.iloc[-2] if len(df) >= 2 else None

        current_price = last_row['close']
        current_sma_short = last_row['SMA_Short']
        current_sma_long = last_row['SMA_Long']

        signal = "HOLD"
        message = "Nenhum sinal claro (SMA)."

        if previous_row is not None:
            previous_sma_short = previous_row['SMA_Short']
            previous_sma_long = previous_row['SMA_Long']

            if previous_sma_short <= previous_sma_long and current_sma_short > current_sma_long:
                signal = "BUY"
                message = f"Sinal de COMPRA: SMA Curta ({self.short_window}) cruzou acima da Longa ({self.long_window})."
            elif previous_sma_short >= previous_sma_long and current_sma_short < current_sma_long:
                signal = "SELL"
                message = f"Sinal de VENDA: SMA Curta ({self.short_window}) cruzou abaixo da Longa ({self.long_window})."

        return {"action": signal, "signal": signal, "price": current_price, "message": message}

class EMACrossoverStrategy(BaseStrategy):
    """
    Estratégia de cruzamento de duas Médias Móveis Exponenciais (EMA).
    Dá maior peso aos dados recentes e reage mais rápido às tendências.
    """
    def __init__(self, short_window=9, long_window=21, logger=None):
        self.short_window = short_window
        self.long_window = long_window
        self.logger = logger
        msg = f"Estratégia EMA Crossover inicializada (Curta={self.short_window}, Longa={self.long_window})"
        if self.logger:
            self.logger.info(msg)
        else:
            print(msg)

    def generate_signal(self, ohlcv_data: pd.DataFrame) -> dict:
        if ohlcv_data.empty or len(ohlcv_data) < max(self.short_window, self.long_window):
            return {"action": "HOLD", "signal": "HOLD", "price": None, "message": "Dados insuficientes para calcular médias móveis exponenciais."}

        df = ohlcv_data.copy()
        df['EMA_Short'] = ta.trend.ema_indicator(df['close'], window=self.short_window)
        df['EMA_Long'] = ta.trend.ema_indicator(df['close'], window=self.long_window)
        df = df.dropna(subset=['EMA_Short', 'EMA_Long'])

        if df.empty:
            return {"action": "HOLD", "signal": "HOLD", "price": None, "message": "Dados insuficientes após cálculo de médias."}

        last_row = df.iloc[-1]
        previous_row = df.iloc[-2] if len(df) >= 2 else None

        current_price = last_row['close']
        current_ema_short = last_row['EMA_Short']
        current_ema_long = last_row['EMA_Long']

        signal = "HOLD"
        message = "Nenhum sinal claro (EMA)."

        if previous_row is not None:
            previous_ema_short = previous_row['EMA_Short']
            previous_ema_long = previous_row['EMA_Long']

            if previous_ema_short <= previous_ema_long and current_ema_short > current_ema_long:
                signal = "BUY"
                message = f"Sinal de COMPRA: EMA Curta ({self.short_window}) cruzou acima da Longa ({self.long_window})."
            elif previous_ema_short >= previous_ema_long and current_ema_short < current_ema_long:
                signal = "SELL"
                message = f"Sinal de VENDA: EMA Curta ({self.short_window}) cruzou abaixo da Longa ({self.long_window})."

        return {"action": signal, "signal": signal, "price": current_price, "message": message}

class MultiPointVectorStrategy(BaseStrategy):
    """
    Estratégia inovadora dos 5 Pontos de Medição (Vetor de Estado).
    Compara o preço atual em tempo real contra 4 médias móveis de diferentes prazos.
    Possui Modo Ágil (4 pontos) e Modo Conservador (5 pontos) com Filtro de Exaustão de Preço.
    """
    def __init__(self, p2_window=9, p3_window=21, p4_window=50, p5_window=200, 
                 mode="AGILE", exhaustion_filter=True, exhaustion_threshold=2.5, p5_filter_active=True, 
                 entry_mode="4PONTOS", exit_mode="P3", logger=None):
        self.p2_window = p2_window  # Muito Rápida (Média 9)
        self.p3_window = p3_window  # Curta (Média 21)
        self.p4_window = p4_window  # Média (Média 50)
        self.p5_window = p5_window  # Longa (Média 200)
        self.mode = mode.upper()     # "AGILE" ou "CONSERVATIVE"
        self.exhaustion_filter = exhaustion_filter
        self.exhaustion_threshold = exhaustion_threshold
        self.p5_filter_active = p5_filter_active
        self.entry_mode = entry_mode.upper() if entry_mode else "4PONTOS"
        self.exit_mode = exit_mode.upper() if exit_mode else "P3"
        self.logger = logger

        msg = (f"Estratégia Vetor de 5 Pontos inicializada | Entrada={self.entry_mode} | Saída={self.exit_mode} | "
               f"P2={self.p2_window}, P3={self.p3_window}, P4={self.p4_window}, P5={self.p5_window} | "
               f"Filtro Exaustão={self.exhaustion_filter} (Limiar={self.exhaustion_threshold}%) | Filtro P5={self.p5_filter_active}")
        if self.logger:
            self.logger.info(msg)
        else:
            print(msg)

    def generate_signal(self, ohlcv_data: pd.DataFrame) -> dict:
        max_window = max(self.p2_window, self.p3_window, self.p4_window, self.p5_window)
        if ohlcv_data.empty or len(ohlcv_data) < max_window:
            return {"action": "HOLD", "signal": "HOLD", "price": None, "message": "Dados insuficientes para calcular os 5 pontos de medição."}

        df = ohlcv_data.copy()
        
        # Calcular as 4 médias móveis simples (SMA) que representam P2, P3, P4 e P5
        df['P2_MA'] = ta.trend.sma_indicator(df['close'], window=self.p2_window)
        df['P3_MA'] = ta.trend.sma_indicator(df['close'], window=self.p3_window)
        df['P4_MA'] = ta.trend.sma_indicator(df['close'], window=self.p4_window)
        df['P5_MA'] = ta.trend.sma_indicator(df['close'], window=self.p5_window)
        
        needed_cols = ['P2_MA', 'P3_MA', 'P4_MA']
        if self.mode == "CONSERVATIVE" or self.p5_filter_active:
            needed_cols.append('P5_MA')
        df = df.dropna(subset=needed_cols)
        
        if df.empty:
            return {"action": "HOLD", "signal": "HOLD", "price": None, "message": "Dados insuficientes após cálculo de vetores."}

        last_row = df.iloc[-1]
        previous_row = df.iloc[-2] if len(df) >= 2 else None

        # Definição dos 5 Pontos Correntes
        p1_curr = last_row['close']   # Preço exato atual
        p2_curr = last_row['P2_MA']   # Média Rápida
        p3_curr = last_row['P3_MA']   # Média Curta
        p4_curr = last_row['P4_MA']   # Média Média
        p5_curr = last_row['P5_MA']   # Média Longa

        # Definição dos 5 Pontos Anteriores (para verificação de gatilho/cruzamento)
        if previous_row is not None:
            p1_prev = previous_row['close']
            p2_prev = previous_row['P2_MA']
            p3_prev = previous_row['P3_MA']
            p4_prev = previous_row['P4_MA']
            p5_prev = previous_row['P5_MA']
        else:
            p1_prev = p2_prev = p3_prev = p4_prev = p5_prev = None

        signal = "HOLD"
        message = "Aguardando alinhamento dos 5 pontos."

        # Avaliação de Alinhamento
        if self.mode == "CONSERVATIVE":
            # Modo Conservador: Exige alinhamento absoluto dos 5 pontos (P1 > P2 > P3 > P4 > P5)
            curr_aligned = (p1_curr > p2_curr) and (p2_curr > p3_curr) and (p3_curr > p4_curr) and (p4_curr > p5_curr)
            prev_aligned = (p1_prev is not None) and (p1_prev > p2_prev) and (p2_prev > p3_prev) and (p3_prev > p4_prev) and (p4_prev > p5_prev)
        else:
            # Modo Ágil (Padrão): Exige alinhamento dos 4 pontos dinâmicos (P1 > P2 > P3 > P4)
            # A de 200 períodos (P5) é usada apenas como filtro de inclinação (slope) para evitar bear markets fortes.
            p5_slope_positive = (p5_prev is not None) and (p5_curr >= p5_prev)
            if self.p5_filter_active:
                curr_aligned = (p1_curr > p2_curr) and (p2_curr > p3_curr) and (p3_curr > p4_curr) and p5_slope_positive
            else:
                curr_aligned = (p1_curr > p2_curr) and (p2_curr > p3_curr) and (p3_curr > p4_curr)
            prev_aligned = (p1_prev is not None) and (p1_prev > p2_prev) and (p2_prev > p3_prev) and (p3_prev > p4_prev)

        # GATILHO DE COMPRA: Acaba de alinhar
        if curr_aligned and not prev_aligned:
            # Validar Filtro de Exaustão (Preço Esticado)
            if self.exhaustion_filter:
                dist_pct = ((p1_curr - p2_curr) / p2_curr) * 100
                if dist_pct > self.exhaustion_threshold:
                    return {
                        "action": "HOLD",
                        "signal": "HOLD",
                        "price": p1_curr,
                        "message": f"🔒 COMPRA BLOQUEADA: Preço muito esticado em relação à Média Rápida ({dist_pct:.2f}% > {self.exhaustion_threshold}%)."
                    }
            
            signal = "BUY"
            message = f"🚀 GATILHO COMPRA (Vetor 5 Pontos - {self.mode}): Alinhamento de tendência detetado!"

        # GATILHO DE VENDA: Perda de suporte
        # Em vez de esperar pelo cruzamento lento de 200, saímos rapidamente se o preço atual cair abaixo da média confirmadora (P3)
        elif (p1_prev is not None) and (p1_curr < p3_curr) and (p1_prev >= p3_prev):
            signal = "SELL"
            message = "⚠️ GATILHO VENDA: Preço caiu abaixo da Média Confirmadora (P3), indicando fim do impulso."

        return {"action": signal, "signal": signal, "price": p1_curr, "message": message}

class StrategyFactory:
    @staticmethod
    def get_strategy(config: dict, logger=None) -> BaseStrategy:
        strategy_type = config.get("STRATEGY_TYPE", "SMA_CROSSOVER")
        
        if strategy_type == "SMA_CROSSOVER":
            return SMACrossoverStrategy(
                short_window=int(config.get("SHORT_WINDOW", 9)),
                long_window=int(config.get("LONG_WINDOW", 21)),
                logger=logger
            )
        elif strategy_type == "EMA_CROSSOVER":
            return EMACrossoverStrategy(
                short_window=int(config.get("SHORT_WINDOW", 9)),
                long_window=int(config.get("LONG_WINDOW", 21)),
                logger=logger
            )
        elif strategy_type == "MULTIPOINT_VECTOR":
            return MultiPointVectorStrategy(
                p2_window=int(config.get("P2_WINDOW", 9)),
                p3_window=int(config.get("P3_WINDOW", 21)),
                p4_window=int(config.get("P4_WINDOW", 50)),
                p5_window=int(config.get("P5_WINDOW", 200)),
                mode=config.get("MULTIPOINT_MODE", "AGILE"),
                exhaustion_filter=config.get("EXHAUSTION_FILTER", True),
                exhaustion_threshold=float(config.get("EXHAUSTION_THRESHOLD", 2.5)),
                p5_filter_active=config.get("P5_SLOPE_FILTER_ACTIVE", True),
                entry_mode=config.get("ENTRY_MODE", "4PONTOS"),
                exit_mode=config.get("EXIT_MODE", "P3"),
                logger=logger
            )
        else:
            return SMACrossoverStrategy(
                short_window=int(config.get("SHORT_WINDOW", 9)),
                long_window=int(config.get("LONG_WINDOW", 21)),
                logger=logger
            )