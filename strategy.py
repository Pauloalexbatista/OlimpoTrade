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
                 entry_mode="4PONTOS", exit_mode="P3", operation_mode="TREND_FOLLOWING", logger=None):
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
        self.operation_mode = operation_mode.upper() if operation_mode else "TREND_FOLLOWING"
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

class PauloGoldStrategy(BaseStrategy):
    """
    Estratégia Exclusiva PAULO_GOLD (Breakout Puro).
    Entrada (BUY): Assim que cruza a 1ª linha quando vai a subir - compra.
    Saída (SELL): Assim que cruza a 1ª linha quando vai a descer - vende.
    """
    def __init__(self, short_window=9, long_window=21, trend_filter=False, min_dist_pct=0.0, logger=None):
        self.short_window = short_window
        self.long_window = long_window
        self.trend_filter = trend_filter
        self.min_dist_pct = min_dist_pct
        self.logger = logger
        msg = f"Estratégia Exclusiva PAULO_GOLD inicializada (Curta={self.short_window}, Longa={self.long_window}, FiltroTendência={self.trend_filter}, DistMin={self.min_dist_pct}%)"
        if self.logger:
            self.logger.info(msg)
        else:
            print(msg)

    def generate_signal(self, ohlcv_data: pd.DataFrame) -> dict:
        if ohlcv_data.empty or len(ohlcv_data) < max(self.short_window, self.long_window):
            return {"action": "HOLD", "signal": "HOLD", "price": None, "message": "Dados insuficientes para calcular médias móveis simples."}

        df = ohlcv_data.copy()
        df['Line_1'] = ta.trend.sma_indicator(df['close'], window=self.short_window)
        df['Line_2'] = ta.trend.sma_indicator(df['close'], window=self.long_window)
        df = df.dropna(subset=['Line_1', 'Line_2'])

        if df.empty:
            return {"action": "HOLD", "signal": "HOLD", "price": None, "message": "Dados insuficientes após cálculo de médias."}

        last_row = df.iloc[-1]
        previous_row = df.iloc[-2] if len(df) >= 2 else None

        current_price = last_row['close']
        current_l1 = last_row['Line_1']
        current_l2 = last_row['Line_2']

        signal = "HOLD"
        message = "Aguardando rompimento..."

        if previous_row is not None:
            previous_price = previous_row['close']
            previous_l1 = previous_row['Line_1']
            previous_l2 = previous_row['Line_2']

            # Gatilhos de Entrada (COMPRA): 
            # 1. Cruzamento de alta de QUALQUER das duas linhas
            cross_above_l1 = (previous_price <= previous_l1) and (current_price > current_l1)
            cross_above_l2 = (previous_price <= previous_l2) and (current_price > current_l2)
            cross_above = cross_above_l1 or cross_above_l2

            # 2. Re-Entrada por Alinhamento (Preço > Azul > Laranja e a subir)
            price_is_growing = (current_price > previous_price)
            reentry_aligned = price_is_growing and (current_price > current_l1) and (current_l1 > current_l2)

            # Gatilhos de Saída (VENDA): Cruzamento de baixa de QUALQUER das duas linhas
            cross_below_l1 = (previous_price >= previous_l1) and (current_price < current_l1)
            cross_below_l2 = (previous_price >= previous_l2) and (current_price < current_l2)
            cross_below = cross_below_l1 or cross_below_l2

            # Filtro de Tendência se ativado
            trend_allows_buy = True
            if self.trend_filter:
                trend_allows_buy = (current_l1 > current_l2 * (1 + self.min_dist_pct / 100.0))

            if (cross_above or reentry_aligned) and trend_allows_buy:
                signal = "BUY"
                if reentry_aligned:
                    message = f"🚀 Re-Entrada por Alinhamento (PAULO_GOLD): Preço em alta ({current_price:.2f} > {current_l1:.2f} > {current_l2:.2f})."
                else:
                    line_name = "Média Curta (Line_1)" if cross_above_l1 else "Média Lenta (Line_2)"
                    message = f"🚀 Sinal de COMPRA (PAULO_GOLD): Preço ({current_price:.2f}) cruzou acima da {line_name}."
            elif cross_below:
                signal = "SELL"
                line_name = "Média Curta (Line_1)" if cross_below_l1 else "Média Lenta (Line_2)"
                message = f"🚨 Sinal de VENDA (PAULO_GOLD): Preço ({current_price:.2f}) cruzou abaixo da {line_name}."
        else:
            # Entrada Imediata se Alinhado no início da simulação
            trend_allows_buy = True
            if self.trend_filter:
                trend_allows_buy = (current_l1 > current_l2 * (1 + self.min_dist_pct / 100.0))
            
            if current_price > max(current_l1, current_l2) and trend_allows_buy:
                signal = "BUY"
                message = f"🚀 Entrada Imediata (PAULO_GOLD): Preço já nasceu alinhado em alta ({current_price:.2f} > {max(current_l1, current_l2):.2f})."

        return {"action": signal, "signal": signal, "price": current_price, "message": message}



class CaterpillarAIStrategy(BaseStrategy):
    """
    Estratégia gerada pela Universidade de Lagartas IA.
    Usa o DNA (Pesos e Threshold) para gerar sinais baseados em 5 sensores.
    """
    def __init__(self, dna, logger=None):
        self.dna = dna
        self.logger = logger
        msg = f"Estratégia IA Lagarta inicializada (Threshold={self.dna.get('threshold', 0):.2f})"
        if self.logger:
            self.logger.info(msg)
        else:
            print(msg)

    def generate_signal(self, ohlcv_data: pd.DataFrame) -> dict:
        if len(ohlcv_data) < 20:
            return {"action": "HOLD", "signal": "HOLD", "price": None, "message": "Dados insuficientes para IA"}
        
        df = ohlcv_data.copy()
        
        # Calcular os mesmos indicadores usados no treino sintético
        df['MA_Fast'] = ta.trend.sma_indicator(df['close'], window=5)
        df['MA_Slow'] = ta.trend.sma_indicator(df['close'], window=12)
        df['MA_200'] = ta.trend.sma_indicator(df['close'], window=20)
        df['Std'] = df['close'].rolling(window=8).std()
        
        delta_l = df['close'].diff()
        gain_l = (delta_l.where(delta_l > 0, 0)).rolling(window=8).mean()
        loss_l = (-delta_l.where(delta_l < 0, 0)).rolling(window=8).mean()
        rs_l = gain_l / (loss_l + 1e-5)
        df['RSI'] = 100 - (100 / (1 + rs_l))
        
        df = df.fillna(method='bfill')
        
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        p_c = last_row['close']
        ma_f_c = last_row['MA_Fast']
        ma_s_c = last_row['MA_Slow']
        ma_f_p = prev_row['MA_Fast']
        ma_200 = last_row['MA_200']
        std_val = last_row['Std']
        rsi_val = last_row['RSI']
        
        # 5 Sensores (Valores binários/trinários)
        s1_trend = 1.0 if (p_c > ma_f_c > ma_s_c) else -1.0
        s2_slope = 1.0 if (ma_f_c > ma_f_p) else -1.0
        s3_vol = -1.0 if (std_val > 6.0) else 1.0
        s4_floor = -1.0 if ((p_c - ma_200)/ma_200 > 0.09) else 1.0
        s5_rsi = 1.0 if (rsi_val < 35) else (-1.0 if rsi_val > 65 else 0.0)
        
        # Score Computado via Pesos Neuronais do DNA
        score = (s1_trend * self.dna.get('w_trend', 0)) + \
                (s2_slope * self.dna.get('w_slope', 0)) + \
                (s3_vol * self.dna.get('w_vol', 0)) + \
                (s4_floor * self.dna.get('w_floor', 0)) + \
                (s5_rsi * self.dna.get('w_rsi', 0))
                
        threshold = self.dna.get('threshold', 999.0)
        
        if score >= threshold:
            msg = f"IA Score: {score:.2f} >= {threshold:.2f} (S1:{s1_trend} S2:{s2_slope} S3:{s3_vol})"
            return {"action": "BUY", "signal": "BUY", "price": p_c, "message": msg}
            
        msg = f"IA Score: {score:.2f} < {threshold:.2f}"
        return {"action": "HOLD", "signal": "HOLD", "price": p_c, "message": msg}

class StrategyFactory:
    @staticmethod
    def get_strategy(config: dict, logger=None) -> BaseStrategy:
        strategy_type = config.get("STRATEGY_TYPE", "SMA_CROSSOVER")
        
        if strategy_type.startswith("🎓"):
            caterpillar_name = strategy_type.replace("🎓 ", "")
            try:
                import json, os
                file_path = "caterpillars.json"
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        caterpillars = json.load(f)
                        if caterpillar_name in caterpillars:
                            dna = caterpillars[caterpillar_name]
                            return CaterpillarAIStrategy(dna=dna, logger=logger)
            except Exception as e:
                if logger: logger.error(f"Erro ao carregar DNA da lagarta {caterpillar_name}: {e}")
            
            # Caso falhe ao carregar o DNA, usamos fallback
            if logger: logger.warning("Fallback para SMACrossover após falha no DNA")
            return SMACrossoverStrategy(logger=logger)
            
        if strategy_type == "PAULO_GOLD":
            return PauloGoldStrategy(
                short_window=int(config.get("SHORT_WINDOW", 9)),
                long_window=int(config.get("LONG_WINDOW", 21)),
                trend_filter=config.get("PAULO_GOLD_TREND_FILTER", False),
                min_dist_pct=float(config.get("PAULO_GOLD_MIN_DIST_PCT", 0.0)),
                logger=logger
            )
        elif strategy_type == "SMA_CROSSOVER":
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
                operation_mode=config.get("OPERATION_MODE", "TREND_FOLLOWING"),
                logger=logger
            )
        else:
            return SMACrossoverStrategy(
                short_window=int(config.get("SHORT_WINDOW", 9)),
                long_window=int(config.get("LONG_WINDOW", 21)),
                logger=logger
            )