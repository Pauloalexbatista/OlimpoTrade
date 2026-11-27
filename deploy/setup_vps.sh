#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VPS_USER="${USER}"

echo "==> A preparar OlimpoTrade em: ${APP_DIR} (utilizador: ${VPS_USER})"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python3 não encontrado. Instala com: sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
  exit 1
fi

if [ ! -d "${APP_DIR}/.venv" ]; then
  python3 -m venv "${APP_DIR}/.venv"
fi

"${APP_DIR}/.venv/bin/pip" install --upgrade pip
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

if [ ! -f "${APP_DIR}/.env" ]; then
  cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
  echo "ATENCAO: Criado ${APP_DIR}/.env a partir de .env.example — preenche as tuas chaves API antes de ligar!"
fi

for svc in olimpo-bot.service olimpo-ui.service; do
  sed -e "s|__APP_DIR__|${APP_DIR}|g" -e "s|__VPS_USER__|${VPS_USER}|g" \
    "${APP_DIR}/deploy/${svc}" | sudo tee "/etc/systemd/system/${svc}" >/dev/null
done

sudo systemctl daemon-reload
sudo systemctl enable olimpo-ui.service
echo "==> Instalação concluída!"
echo "    1) Edita ${APP_DIR}/.env com as tuas chaves"
echo "    2) Para iniciar o Dashboard: sudo systemctl start olimpo-ui.service"
echo "    3) Para iniciar o Motor 24h: sudo systemctl enable --now olimpo-bot.service"
