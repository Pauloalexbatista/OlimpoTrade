# my_trading_bot/crypto_news_service.py
import urllib.request
import xml.etree.ElementTree as ET
import html
import re

class CryptoNewsService:
    def __init__(self, logger=None):
        self.logger = logger
        self.rss_sources = [
            "https://cointelegraph.com/rss",
            "https://www.coindesk.com/arc/outboundfeeds/rss/"
        ]

    def fetch_news(self):
        # Tenta CoinTelegraph primeiro, faz fallback para CoinDesk em caso de falha de rede
        for source in self.rss_sources:
            try:
                req = urllib.request.Request(source, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    xml_data = response.read()
                
                # Corrigir potenciais problemas de parsing de XML se houver tags mal formadas
                root = ET.fromstring(xml_data)
                news_items = []
                
                # Obter os 10 artigos mais recentes
                for item in root.findall(".//item")[:10]:
                    title = item.find("title").text if item.find("title") is not None else "Sem título"
                    link = item.find("link").text if item.find("link") is not None else "#"
                    pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                    description = item.find("description").text if item.find("description") is not None else ""
                    
                    # Limpar tags HTML da descrição (como imagens inline ou embeds do Cointelegraph)
                    clean_desc = re.sub('<[^<]+?>', '', description)
                    clean_desc = html.unescape(clean_desc).strip()
                    
                    # Truncar descrição longa para estética premium da UI
                    if len(clean_desc) > 180:
                        clean_desc = clean_desc[:180] + "..."
                    elif clean_desc == "":
                        clean_desc = "Sem resumo disponível. Clique no link para ler a notícia completa."
                    
                    # Analisar o Sentimento da notícia
                    sentiment = self.analyze_sentiment(title + " " + clean_desc)
                    
                    news_items.append({
                        "title": html.unescape(title).strip(),
                        "link": link.strip(),
                        "date": pub_date.strip(),
                        "desc": clean_desc,
                        "sentiment": sentiment
                    })
                
                if news_items:
                    return news_items
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to fetch news from {source}: {e}")
                continue
                
        raise Exception("Não foi possível carregar notícias de nenhuma das fontes disponíveis. Verifique a sua ligação à internet.")

    def analyze_sentiment(self, text):
        # Dicionários de palavras-chave para análise de sentimento rápida e sem dependências pesadas
        positive_words = {
            "bullish", "bull", "surge", "rise", "skyrocket", "gain", "breakout", 
            "approve", "positive", "growth", "jump", "climb", "high", "success", 
            "win", "record", "rally", "pump", "adoption", "partner", "buy", "up",
            "alta", "subida", "aprova", "positivo", "crescimento", "sucesso", "ganho",
            "compra", "parceria", "adopção", "recorde"
        }
        negative_words = {
            "bearish", "bear", "crash", "drop", "dump", "fall", "collapse", 
            "decline", "negative", "warn", "suspend", "ban", "lawsuit", "sue", 
            "hack", "scam", "theft", "drain", "down", "low", "panic", "fear", "sell",
            "baixa", "queda", "queda", "colapso", "negativo", "aviso", "banir", "processo",
            "roubo", "esquema", "pânico", "medo", "venda", "perda"
        }
        
        # Tokenizar texto em palavras
        words = re.findall(r'\w+', text.lower())
        pos_count = sum(1 for w in words if w in positive_words)
        neg_count = sum(1 for w in words if w in negative_words)
        
        if pos_count > neg_count:
            return "🟢 Alta (Bullish)"
        elif neg_count > pos_count:
            return "🔴 Baixa (Bearish)"
        else:
            return "⚪ Neutro"

if __name__ == "__main__":
    service = CryptoNewsService()
    try:
        articles = service.fetch_news()
        print(f"--- Encontradas {len(articles)} notícias ---")
        for i, art in enumerate(articles[:2]):
            print(f"\n{i+1}. {art['title']}")
            print(f"Sentimento: {art['sentiment']} | Data: {art['date']}")
            print(f"Resumo: {art['desc']}")
    except Exception as e:
        print(f"Erro no serviço de notícias: {e}")
