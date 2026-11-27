# 🚀 Guia de Deploy na VPS (Ubuntu / Debian 24h)

Este projeto está pronto para correr 24h por dia numa VPS Linux com **systemd** (reinicia automaticamente se o servidor reiniciar ou se houver falha de rede).

## 1. Pré-requisitos na VPS
```bash
sudo apt update && sudo apt install -y git python3 python3-venv python3-pip
```

## 2. Copiar o projeto e instalar
```bash
cd ~
# Copia a pasta PRJT_OlimpoTrade para a VPS (via git clone ou scp)
cd PRJT_OlimpoTrade
chmod +x deploy/setup_vps.sh
./deploy/setup_vps.sh
```

## 3. Configurar chaves (`.env`)
Edita o ficheiro `.env` na raiz do projeto:
```bash
nano .env
```
Garante que tens:
- `ALPACA_API_KEY=...`
- `ALPACA_SECRET_KEY=...`
- `ALPACA_PAPER=true` (para Paper Trading) ou `false` (apenas quando entrares em Real).

## 4. Iniciar os Serviços
- **Painel Web (Streamlit na porta 8501):**
  ```bash
  sudo systemctl start olimpo-ui.service
  sudo systemctl status olimpo-ui.service
  ```
- **Motor Autónomo 24h (`main.py` — independente do browser):**
  ```bash
  sudo systemctl enable --now olimpo-bot.service
  sudo systemctl status olimpo-bot.service
  ```

## 5. Segurança recomendada na VPS
- Não deixes a porta `8501` aberta ao público sem proteção: usa um túnel SSH (`ssh -L 8501:localhost:8501 user@IP_DA_VPS`) ou configura firewall (`ufw allow OpenSSH`) + HTTPS com Nginx/Caddy.
- Mantém `validated_for_live: false` em `trained_best_strategy.json` e `mode: DRY_RUN` em `bot_live_control.json` até validares na Parte 2.
