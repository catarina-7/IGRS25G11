# FROM kamailio/kamailio:5.7

USER root

# Instalar módulos necessários
RUN apt-get update && apt-get install -y \
    kamailio-mysql-modules \
    kamailio-extra-modules \
    kamailio-python3-modules \
    python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Copiar config
COPY kamailio.cfg /etc/kamailio/kamailio.cfg

# Copiar SQL inicial (opcional)
COPY database.sql /docker-entrypoint-initdb.d/database.sql

USER kamailio
