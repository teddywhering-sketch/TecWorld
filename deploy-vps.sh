#!/bin/bash
# Deploy do TecWorld na VPS de produção.
# Uso: ./deploy-vps.sh   (executado da máquina local, requer acesso SSH à VPS)

set -e

VPS="${VPS:-root@145.223.92.203}"
APP_DIR="/srv/TecWorld"

echo "### Enviando código local (commit atual) para $VPS:$APP_DIR ..."
git archive HEAD | ssh -o ConnectTimeout=15 "$VPS" "mkdir -p '$APP_DIR' && tar -x -C '$APP_DIR'"

echo "### Executando deploy na VPS..."
ssh -o ConnectTimeout=15 "$VPS" APP_DIR="$APP_DIR" 'bash -s' <<'REMOTE'
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
