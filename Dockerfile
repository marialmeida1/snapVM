# Use a minimal base image
FROM debian:bookworm-slim

# Install system dependencies, PostgreSQL, and Node.js
RUN apt-get update && apt-get install -y \
    postgresql postgresql-contrib \
    curl \
    systemd \
    sysvinit-core \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configure PostgreSQL to accept connections
USER postgres
RUN /etc/init.d/postgresql start && \
    psql --command "CREATE USER admin WITH SUPERUSER PASSWORD 'admin';" && \
    createdb -O admin app_db && \
    /etc/init.d/postgresql stop
RUN echo "host all all 0.0.0.0/0 md5" >> /etc/postgresql/15/main/pg_hba.conf
RUN echo "listen_addresses='*'" >> /etc/postgresql/15/main/postgresql.conf
USER root

# Create the working directory for our Node.js app
WORKDIR /opt/app
COPY src/ /opt/app/

# Set up an init script (Firecracker requires an init process like systemd or a custom script)
COPY init.sh /sbin/init.sh
RUN chmod +x /sbin/init.sh

# Set the default entrypoint for the microVM
CMD ["/sbin/init.sh"]
