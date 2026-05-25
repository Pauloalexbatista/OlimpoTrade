# my_trading_bot/daily_market_scanner.py
import json
import urllib.request
import urllib.error

class DailyMarketScanner:
    def __init__(self, logger=None):
        self.logger = logger
        self.api_url = "https://api.binance.com/api/v3/ticker/24hr"

    def scan_market(self):
        try:
            req = urllib.request.Request(self.api_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                raw_data = json.loads(response.read().decode())
        except urllib.error.URLError as e:
            if self.logger:
                self.logger.error(f"Error fetching data from Binance: {e}")
            raise Exception(f"Erro ao ligar à API da Binance: {e}")

        # Lista de stablecoins a ignorar para focar em ativos voláteis transacionáveis
        stablecoins = {
            "USDTUSDT", "USDCUSDT", "BUSDUSDT", "FDUSDUSDT", "TUSDUSDT", 
            "DAIUSDT", "EURUSDT", "GBPUSDT", "AUDUSDT", "AEURUSDT", "PAXGUSDT",
            "USDCUSDC", "FDUSDUSDC"
        }

        scanner_results = []
        for ticker in raw_data:
            symbol = ticker["symbol"]
            
            # Filtrar por pares USDT e excluir stablecoins
            if symbol.endswith("USDT") and symbol not in stablecoins:
                try:
                    price_change_pct = float(ticker["priceChangePercent"])
                    quote_volume = float(ticker["quoteVolume"])
                    last_price = float(ticker["lastPrice"])
                    high_price = float(ticker["highPrice"])
                    low_price = float(ticker["lowPrice"])
                except (ValueError, TypeError):
                    continue

                # Formatar o par de forma legível (ex: BTC/USDT)
                pair_formatted = f"{symbol[:-4]}/USDT"

                scanner_results.append({
                    "Criptomoeda": pair_formatted,
                    "Preço Atual (USDT)": last_price,
                    "Variação 24h (%)": price_change_pct,
                    "Volume 24h (USDT)": quote_volume,
                    "Máxima 24h (USDT)": high_price,
                    "Mínima 24h (USDT)": low_price
                })

        # 1. Top 10 por Volume (Mais Transacionadas / Maior Interesse de Mercado)
        top_volume = sorted(scanner_results, key=lambda x: x["Volume 24h (USDT)"], reverse=True)[:10]

        # 2. Top 10 Maiores Subidas (Gainers com volume mínimo de 1.5M USDT para filtrar ruído de moedas mortas)
        gainers_candidates = [item for item in scanner_results if item["Volume 24h (USDT)"] >= 1500000.0]
        top_gainers = sorted(gainers_candidates, key=lambda x: x["Variação 24h (%)"], reverse=True)[:10]

        return top_volume, top_gainers

if __name__ == "__main__":
    scanner = DailyMarketScanner()
    try:
        vol, gain = scanner.scan_market()
        print("--- Top 3 por Volume ---")
        for i, item in enumerate(vol[:3]):
            print(f"{i+1}. {item['Criptomoeda']} - Vol: {item['Volume 24h (USDT)'] / 1e6:.1f}M USDT - Variação: {item['Variação 24h (%)']:.2f}%")
        print("\n--- Top 3 Gainers ---")
        for i, item in enumerate(gain[:3]):
            print(f"{i+1}. {item['Criptomoeda']} - Variação: {item['Variação 24h (%)']:.2f}% - Vol: {item['Volume 24h (USDT)'] / 1e6:.1f}M USDT")
    except Exception as e:
        print(f"Erro no scanner: {e}")
