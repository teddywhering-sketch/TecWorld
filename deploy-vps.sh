#!/bin/bash
# Deploy do TecWorld na VPS a partir da máquina local.
# Uso: ./deploy-vps.sh   (requer acesso SSH à VPS)
#
# Envia o código do commit atual via SSH e executa o deploy_pro.sh na VPS,
# que cuida de todo o resto (docker, firewall, SSL, serviços, migrações).

set -euo pipefail

VPS="${VPS:-root@145.223.92.203}"
APP_DIR="/srv/TecWorld"

echo "### Enviando código local (commit atual) para $VPS:$APP_DIR ..."
git archive HEAD | ssh -o ConnectTimeout=15 "$VPS" "mkdir -p '$APP_DIR' && tar -x -C '$APP_DIR'"

echo "### Executando deploy_pro.sh na VPS..."
ssh -t -o ConnectTimeout=15 "$VPS" "cd '$APP_DIR' && ./deploy_pro.sh"
