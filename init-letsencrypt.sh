#!/bin/bash

if ! [ -x "$(command -v docker)" ]; then
  echo 'Error: docker is not installed.' >&2
  exit 1
fi

domains=(teddytecworld.tech www.teddytecworld.tech)
rsa_key_size=4096
data_path="./data/certbot"
email="admin@teddytecworld.tech" # Você pode trocar pelo seu email verdadeiro se desejar
staging=0 # Mude para 1 se quiser apenas testar sem bater limite do Let's Encrypt

if [ -d "$data_path" ]; then
  read -p "Já existem dados do certbot na pasta $data_path. Deseja substituir os certificados existentes? (y/N) " decision
  if [ "$decision" != "Y" ] && [ "$decision" != "y" ]; then
    exit
  fi
fi

echo "### Baixando os parâmetros TLS de segurança recomendados..."
mkdir -p "$data_path/conf"
cat > "$data_path/conf/options-ssl-nginx.conf" << 'EOF'
ssl_session_cache shared:le_nginx_SSL:10m;
ssl_session_timeout 1440m;
ssl_session_tickets off;

ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers off;

ssl_ciphers "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384";
EOF
openssl dhparam -out "$data_path/conf/ssl-dhparams.pem" 2048
echo

echo "### Criando certificado 'falso' para Nginx poder iniciar..."
path="/etc/letsencrypt/live/$domains"
mkdir -p "$data_path/conf/live/$domains"
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:$rsa_key_size -days 1\
    -keyout '$path/privkey.pem' \
    -out '$path/fullchain.pem' \
    -subj '/CN=localhost'" certbot
echo

echo "### Iniciando Nginx ..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --force-recreate -d nginx
echo

echo "### Deletando certificado 'falso'..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm --entrypoint "\
  rm -Rf /etc/letsencrypt/live/$domains && \
  rm -Rf /etc/letsencrypt/archive/$domains && \
  rm -Rf /etc/letsencrypt/renewal/$domains.conf" certbot
echo

echo "### Solicitando certificado real do Let's Encrypt..."
domain_args=""
for domain in "${domains[@]}"; do
  domain_args="$domain_args -d $domain"
done

# Seleciona o email
case "$email" in
  "") email_arg="--register-unsafely-without-email" ;;
  *) email_arg="--email $email" ;;
esac

# Habilita staging mode
if [ $staging != "0" ]; then staging_arg="--staging"; fi

docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $staging_arg \
    $email_arg \
    $domain_args \
    --rsa-key-size $rsa_key_size \
    --agree-tos \
    --force-renewal \
    --non-interactive" certbot
echo

echo "### Recarregando Nginx para aplicar o certificado..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec nginx nginx -s reload
