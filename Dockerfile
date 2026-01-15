FROM rasa/rasa:3.6.20

ENV RASA_TELEMETRY_DEBUG=false

# Become root
USER root

# Install system dependencies first
# These rarely change => Docker cache them
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    postgresql-client \
    libpq-dev \
    gcc \
    dos2unix \
    curl \
    lsb-release \
    gnupg \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir spacy==3.7.6 \
    && python -m spacy download el_core_news_md
#     && pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the app
COPY server.sh ./
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY models/ ./models/
COPY actions/ ./actions/

# Copy rasa important files
COPY config.yml domain.yml credentials.yml endpoints.yml ./

# Copy .env from actions if it exists
RUN [ -f /app/actions/.env ] && cp /app/actions/.env /app/.env || echo ".env not found, skipping copy"

# Check if requirements.txt exists and install dependencies if present
RUN test -f /app/scripts/store-bot-event-data/requirements.txt && pip install --no-cache-dir -r /app/scripts/store-bot-event-data/requirements.txt || true

# Setup cron jobs
RUN echo "0 * * * * /opt/venv/bin/python /app/scripts/store-bot-event-data/main.py >> /var/log/store-bot-event-data.log 2>&1" > /etc/cron.d/mycron && \
    echo "5 * * * * /opt/venv/bin/python /app/scripts/gid0001/gid0001.py >> /var/log/gid0001.log 2>&1" >> /etc/cron.d/mycron && \
    echo "1 0 * * MON /opt/venv/bin/python /app/scripts/gid0002/gid0002.py >> /var/log/gid0002.log 2>&1" >> /etc/cron.d/mycron && \
    echo "10 * * * * /opt/venv/bin/python /app/scripts/gid0007/gid0007.py >> /var/log/gid0007.log 2>&1" >> /etc/cron.d/mycron && \
    echo "15 * * * * /opt/venv/bin/python /app/scripts/gid0008/gid0008.py >> /var/log/gid0008.log 2>&1" >> /etc/cron.d/mycron && \
    chmod 0644 /etc/cron.d/mycron

# Load crontab
RUN crontab /etc/cron.d/mycron

# Make server script executable
RUN chmod +x server.sh

# Expose Rasa API port
EXPOSE 5005

ENTRYPOINT []

# Start cron and Rasa
CMD ["/bin/sh", "-c", "cron && tail -f /var/log/*.log & ./server.sh"]
