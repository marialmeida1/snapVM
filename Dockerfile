FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    postgresql postgresql-contrib \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER postgres
RUN /etc/init.d/postgresql start && \
    psql --command "CREATE USER admin WITH SUPERUSER PASSWORD 'admin';" && \
    createdb -O admin app_db && \
    /etc/init.d/postgresql stop
RUN echo "host all all 0.0.0.0/0 md5" >> /etc/postgresql/15/main/pg_hba.conf
RUN echo "listen_addresses='*'" >> /etc/postgresql/15/main/postgresql.conf
USER root

WORKDIR /opt/app
COPY src/package.json /opt/app/
RUN npm install --production
COPY src/server.js /opt/app/

COPY init.sh /sbin/init.sh
RUN chmod +x /sbin/init.sh

CMD ["/sbin/init.sh"]
