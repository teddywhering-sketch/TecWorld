#!/bin/bash
# Deploy do TecWorld na VPS de produção.
# Uso: ./deploy-vps.sh   (executado da máquina local, requer acesso SSH à VPS)

set -e

VPS="${VPS:-root@145.223.92.203}"
REPO_URL="https://github.com/teddywhering-sketch/TecWorld.git"
APP_DIR="/srv/TecWorld"

echo "### Conectando em $VPS ..."
ssh -o ConnectTimeout=15 "$VPS" REPO_URL="$REPO_URL" APP_DIR="$APP_DIR" 'bash -s' <<'REMOTE'
set -e

echo "### [VPS] Verificando Docker..."
if ! command -v docker >/dev/null 2>&1; then
  echo "### [VPS] Instalando Docker..."
  curl -fsSL https://get.docker.com | sh
fi

echo "### [VPS] Liberando portas 80/443 no firewall (se ativo)..."
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
  ufw allow 80/tcp
  ufw allow 443/tcp
fi

echo "### [VPS] Atualizando código..."
mkdir -p "$(dirname "$APP_DIR")"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch origin
  git -C "$APP_DIR" reset --hard origin/main
else
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

echo "### [VPS] Build da imagem..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

if [ ! -d data/certbot/conf/live/teddytecworld.tech ]; then
  echo "### [VPS] Certificado ainda não existe — emitindo via Let's Encrypt..."
  yes y | ./init-letsencrypt.sh
else
  echo "### [VPS] Certificado já existe — pulando emissão."
fi

echo "### [VPS] Subindo a stack de produção..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
REMOTE

echo
echo "### Deploy concluído. Testando HTTPS..."
sleep 3
curl -sSI https://teddytecworld.tech | head -5 || echo "(HTTPS ainda não respondeu — verifique os logs na VPS)"
