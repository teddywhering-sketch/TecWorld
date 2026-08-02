#!/bin/bash
# ============================================================================
# deploy_pro.sh — Deploy de produção do TecWorld (executar NA VPS)
#
# Uso:  ./deploy_pro.sh
#
# Idempotente: pode ser executado em todo deploy. Cuida de:
#   1. Docker + plugin compose (instala se faltar)
#   2. Firewall (libera 80/443 se o ufw estiver ativo)
#   3. Atualização do código (git pull, se for um clone git)
#   4. Segredos (.env.prod): gera SECRET_KEY e senha do Postgres fortes
#      no primeiro deploy; sincroniza .env para o docker compose
#   5. Build da imagem
#   6. Certificado SSL Let's Encrypt (emite no primeiro deploy; depois a
#      renovação automática fica por conta do container certbot)
#   7. Sobe/atualiza os serviços (db, web, nginx, certbot) + migrações
#   8. Teste de fumaça (HTTP e HTTPS)
# ============================================================================

set -euo pipefail

DOMAIN="teddytecworld.tech"
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

log() { printf '\n\033[1;32m### %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m>>> %s\033[0m\n' "$*"; }
die() { printf '\033[1;31m!!! %s\033[0m\n' "$*" >&2; exit 1; }

# ----------------------------------------------------------------------------
log "1/8 Verificando Docker..."
if ! command -v docker >/dev/null 2>&1; then
  warn "Docker não encontrado — instalando..."
  curl -fsSL https://get.docker.com | sh
fi
docker info >/dev/null 2>&1 || die "Sem permissão para usar o Docker. Execute como root (ou adicione o usuário ao grupo docker)."
docker compose version >/dev/null 2>&1 || die "Plugin 'docker compose' não encontrado. Instale o pacote docker-compose-plugin."

# ----------------------------------------------------------------------------
log "2/8 Verificando firewall..."
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
  ufw allow 80/tcp >/dev/null
  ufw allow 443/tcp >/dev/null
  warn "Portas 80/443 liberadas no ufw."
else
  warn "ufw inativo ou ausente — nada a fazer. (Se usar o firewall do painel da Hostinger, libere 80/443 lá.)"
fi

# ----------------------------------------------------------------------------
log "3/8 Atualizando código..."
if [ -d .git ]; then
  git pull --ff-only || warn "git pull falhou (alterações locais ou sem rede) — seguindo com o código atual."
else
  warn "Diretório sem .git (código enviado via rsync/tar) — seguindo com o código atual."
fi

# ----------------------------------------------------------------------------
log "4/8 Configurando segredos de produção..."
[ -f .env.prod ] || die "Arquivo .env.prod não encontrado."

# SECRET_KEY forte no primeiro deploy (se ainda for o placeholder)
if grep -q '^SECRET_KEY=desenvolvimento-apenas-altere-em-producao$' .env.prod; then
  NEW_KEY="$(openssl rand -hex 48)"
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${NEW_KEY}|" .env.prod
  warn "SECRET_KEY forte gerada em .env.prod."
fi

# Senha forte do Postgres — só é seguro trocar ANTES do volume de dados existir
if ! docker volume inspect tecworld_postgres_data >/dev/null 2>&1; then
  if grep -q '^POSTGRES_PASSWORD=provedor$' .env.prod; then
    NEW_PW="$(openssl rand -hex 24)"
    sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${NEW_PW}|" .env.prod
    warn "Senha forte do Postgres gerada em .env.prod."
  fi
else
  warn "Volume do Postgres já existe — mantendo a senha atual."
fi

# O serviço 'db' lê POSTGRES_* via substituição de variáveis do compose (arquivo
# .env), enquanto o 'web' lê o .env.prod. Sincroniza para manter consistência.
cp .env.prod .env
warn ".env sincronizado a partir do .env.prod."

# ----------------------------------------------------------------------------
log "5/8 Build da imagem..."
$COMPOSE build

# ----------------------------------------------------------------------------
log "6/8 Certificado SSL (Let's Encrypt)..."
if [ -f "data/certbot/conf/live/${DOMAIN}/fullchain.pem" ]; then
  warn "Certificado já existe — renovação automática fica com o container certbot."
else
  warn "Certificado ainda não existe — emitindo agora..."
  yes y | ./init-letsencrypt.sh
  [ -f "data/certbot/conf/live/${DOMAIN}/fullchain.pem" ] || die "Emissão do certificado falhou. Verifique: DNS do domínio apontando para esta VPS e porta 80 acessível da internet."
fi

# ----------------------------------------------------------------------------
log "7/8 Subindo os serviços..."
$COMPOSE up -d --remove-orphans
# Recria web para carregar o código novo e rodar migrações/collectstatic
$COMPOSE up -d --force-recreate --no-deps web
# Recarrega o nginx para aplicar certificado/configuração sem derrubar conexões
$COMPOSE exec nginx nginx -s reload || $COMPOSE restart nginx

# ----------------------------------------------------------------------------
log "8/8 Teste de fumaça..."
sleep 5
$COMPOSE ps
echo

HTTP_CODE="$(curl -s -o /dev/null -w '%{http_code}' -m 10 "http://${DOMAIN}/" || true)"
HTTPS_CODE="$(curl -s -o /dev/null -w '%{http_code}' -m 10 "https://${DOMAIN}/" || true)"
echo "HTTP  http://${DOMAIN}/  -> ${HTTP_CODE} (esperado: 301)"
echo "HTTPS https://${DOMAIN}/ -> ${HTTPS_CODE} (esperado: 200 ou 302)"

case "$HTTPS_CODE" in
  2*|3*) log "Deploy concluído com sucesso: https://${DOMAIN}" ;;
  *)
    warn "HTTPS ainda não respondeu como esperado. Últimos logs:"
    $COMPOSE logs --tail=30 web nginx
    die "Verifique os logs acima."
    ;;
esac
