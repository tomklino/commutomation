FROM nginx:alpine

RUN apk add --no-cache \
    bash \
    ca-certificates \
    fuse \
    openssl \
    gettext \
    go

RUN go install github.com/googlecloudplatform/gcsfuse@latest && \
    mv /root/go/bin/gcsfuse /usr/local/bin/gcsfuse && \
    rm -rf /root/go && \
    apk del go

COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY entrypoint.sh /entrypoint.sh
COPY 404.html /usr/share/nginx/html/404.html

RUN chmod +x /entrypoint.sh && \
    rm -f /etc/nginx/conf.d/default.conf

ENV HOSTNAME="_" \
    HTTP_PORT="80" \
    HTTPS_PORT="443" \
    CERTS_PATH="/etc/certs.d" \
    BACKEND_URL="" \
    GCS_BUCKET=""

EXPOSE 80 443

ENTRYPOINT ["/entrypoint.sh"]
