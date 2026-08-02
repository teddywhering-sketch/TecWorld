#!/bin/bash
# ============================================================================
# deploy_pro.sh — Deploy de produção do TecWorld (executar NA VPS)
#
# Uso:  ./deploy_pro.sh
#
# Idempotente: pode ser executado em todo deploy. Cuida de:
#   1. Docker + plugin compose (instala se faltar)
#   2. Firewall (libera 80/443 se o ufw estiver ativo)
#   3. Portas 80/443 (detecta Apache/nginx do sistema ocupando as portas)
#   4. Atualização do código (git pull, se for um clone git)
#   5. Segredos: gera SECRET_KEY e senha do Postgres fortes no primeiro
#      deploy (guardados em .env.prod.local, fora do git); sincroniza .env
#   6. Build da imagem
#   7. Certificado SSL Let's Encrypt (emite no primeiro deploy; depois a
#      renovação automática fica por conta do container certbot)
#   8. Sobe/atualiza os serviços (db, web, nginx, certbot) + migrações
#   9. Teste de fumaça (HTTP e HTTPS)
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
log "1/9 Verificando Docker..."
if ! command -v docker >/dev/null 2>&1; then
  warn "Docker não encontrado — instalando..."
  curl -fsSL https://get.docker.com | sh
fi
docker info >/dev/null 2>&1 || die "Sem permissão para usar o Docker. Execute como root (ou adicione o usuário ao grupo docker)."
docker compose version >/dev/null 2>&1 || die "Plugin 'docker compose' não encontrado. Instale o pacote docker-compose-plugin."

# ----------------------------------------------------------------------------
log "2/9 Verificando firewall..."
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
  ufw allow 80/tcp >/dev/null
  ufw allow 443/tcp >/dev/null
  warn "Portas 80/443 liberadas no ufw."
else
  warn "ufw inativo ou ausente — nada a fazer. (Se usar o firewall do painel da Hostinger, libere 80/443 lá.)"
fi

# ----------------------------------------------------------------------------
log "3/9 Verificando portas 80/443..."
for port in 80 443; do
  listener="$(ss -tlnp 2>/dev/null | awk -v p=":${port}\$" '$4 ~ p {print $NF}' | head -1)"
  if [ -n "$listener" ] && ! printf '%s' "$listener" | grep -q docker; then
    die "A porta ${port} já está em uso por outro serviço do sistema: ${listener}
    Pare e desabilite antes de continuar, ex.: systemctl disable --now apache2 (ou nginx) e rode o script de novo."
  fi
done
warn "Portas 80/443 disponíveis (ou já em uso pela própria stack)."

# ----------------------------------------------------------------------------
log "4/9 Atualizando código..."
if [ -d .git ]; then
  git pull --ff-only || warn "git pull falhou (alterações locais ou sem rede) — seguindo com o código atual."
else
  warn "Diretório sem .git (código enviado via rsync/tar) — seguindo com o código atual."
fi

# ----------------------------------------------------------------------------
log "5/9 Configurando segredos de produção..."
[ -f .env.prod ] || die "Arquivo .env.prod não encontrado."
touch .env.prod.local

# SECRET_KEY forte gerada uma única vez, guardada fora do git (.env.prod.local)
if ! grep -q '^SECRET_KEY=' .env.prod.local; then
  echo "SECRET_KEY=$(openssl rand -hex 48)" >> .env.prod.local
  warn "SECRET_KEY forte gerada em .env.prod.local."
fi

# Senha forte do Postgres — só é seguro definir ANTES do volume de dados existir
if ! grep -q '^POSTGRES_PASSWORD=' .env.prod.local; then
  if ! docker volume inspect tecworld_postgres_data >/dev/null 2>&1; then
    echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)" >> .env.prod.local
    warn "Senha forte do Postgres gerada em .env.prod.local."
  else
    warn "Volume do Postgres já existe — mantendo a senha atual."
  fi
fi

# O serviço 'db' lê POSTGRES_* via substituição de variáveis do compose (arquivo
# .env), enquanto o 'web' lê .env.prod + .env.prod.local. Concatena para manter
# consistência (em .env, a última ocorrência de uma chave vence).
cat .env.prod .env.prod.local > .env
warn ".env sincronizado a partir de .env.prod + .env.prod.local."

# ----------------------------------------------------------------------------
log "6/9 Build da imagem..."
$COMPOSE build

# ----------------------------------------------------------------------------
log "7/9 Certificado SSL (Let's Encrypt)..."
CERT="data/certbot/conf/live/${DOMAIN}/fullchain.pem"
# O init-letsencrypt.sh cria um certificado "falso" (CN=localhost) no mesmo
# caminho para o nginx conseguir iniciar — a simples existência do arquivo
# não prova que o certificado real foi emitido.
cert_ok() {
  [ -f "$CERT" ] && ! openssl x509 -in "$CERT" -noout -subject 2>/dev/null | grep -q "CN *= *localhost"
}
if cert_ok; then
  warn "Certificado já existe — renovação automática fica com o container certbot."
else
  warn "Certificado real ainda não existe — emitindo agora..."
  echo y | ./init-letsencrypt.sh
  cert_ok || die "Emissão do certificado falhou (o nginx segue com o certificado provisório).
    Leia a saída do certbot acima para o motivo. Checagens: DNS de ${DOMAIN} e www
    apontando para esta VPS, porta 80 acessível da internet e limite de tentativas
    do Let's Encrypt (5 falhas/hora por domínio)."
fi

# ----------------------------------------------------------------------------
log "8/9 Subindo os serviços..."
$COMPOSE up -d --remove-orphans
# Recria web para carregar o código novo e rodar migrações/collectstatic
$COMPOSE up -d --force-recreate --no-deps web
# Recarrega o nginx para aplicar certificado/configuração sem derrubar conexões
$COMPOSE exec nginx nginx -s reload || $COMPOSE restart nginx

# ----------------------------------------------------------------------------
log "9/9 Teste de fumaça..."
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
