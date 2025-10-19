#!/bin/bash
set -e

HOSTNAME=${HOSTNAME:-"_"}
HTTP_PORT=${HTTP_PORT:-80}
HTTPS_PORT=${HTTPS_PORT:-443}
CERTS_PATH=${CERTS_PATH:-"/etc/certs.d"}
BACKEND_URL=${BACKEND_URL:-""}
GCS_BUCKET=${GCS_BUCKET:-""}

echo "Starting Gateway service..."
echo "Configuration:"
echo "  HOSTNAME: $HOSTNAME"
echo "  HTTP_PORT: $HTTP_PORT"
echo "  HTTPS_PORT: $HTTPS_PORT"
echo "  CERTS_PATH: $CERTS_PATH"
echo "  BACKEND_URL: $BACKEND_URL"
echo "  GCS_BUCKET: $GCS_BUCKET"

mkdir -p /mnt/gcs

if [ -n "$GCS_BUCKET" ]; then
    echo "Mounting GCS bucket: $GCS_BUCKET"
    gcsfuse --implicit-dirs "$GCS_BUCKET" /mnt/gcs
else
    echo "WARNING: GCS_BUCKET not set, using local /mnt/gcs directory"
fi

echo "Generating nginx configuration..."

if [ -n "$BACKEND_URL" ]; then
    echo "Backend URL configured: $BACKEND_URL"
    export HOSTNAME HTTP_PORT HTTPS_PORT CERTS_PATH BACKEND_URL
    envsubst '${HOSTNAME} ${HTTP_PORT} ${HTTPS_PORT} ${CERTS_PATH} ${BACKEND_URL}' < /etc/nginx/nginx.conf.template > /etc/nginx/conf.d/default.conf
else
    echo "WARNING: BACKEND_URL not set, /api/ requests will not be proxied"
    export HOSTNAME HTTP_PORT HTTPS_PORT CERTS_PATH
    cat /etc/nginx/nginx.conf.template | sed '/location \/api\//,/^    }/d' | envsubst '${HOSTNAME} ${HTTP_PORT} ${HTTPS_PORT} ${CERTS_PATH}' > /etc/nginx/conf.d/default.conf
fi

if [ ! -f "$CERTS_PATH/cert.pem" ] || [ ! -f "$CERTS_PATH/key.pem" ]; then
    echo "WARNING: SSL certificates not found at $CERTS_PATH, generating self-signed certificate..."
    mkdir -p "$CERTS_PATH"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$CERTS_PATH/key.pem" \
        -out "$CERTS_PATH/cert.pem" \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$HOSTNAME"
fi

echo "Starting nginx..."
nginx -g 'daemon off;'
