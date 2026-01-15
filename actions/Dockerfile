######################################################################
#  Use this Dockerfile to build a standalone image with your actions #
######################################################################
# Μέσα στο image του rasa-sdk:3.1.1 γίνεται ΑΥΤΟΜΑΤΑ expose το 5055 port αλλά φυσικα
# τροποποιείται από το docker-compose.yml στο port που θελουμε (το αφήνω 5055)

FROM rasa/rasa-sdk:3.6.2

WORKDIR /app

# Change back to root user to install dependencies γιατί ξεκινάει απο USER 1001 κανονικά
USER root

# Install Greek locale
RUN apt-get update && apt-get install -y locales
RUN locale-gen el_GR.UTF-8

# Set the locale environment variable
ENV LC_ALL el_GR.UTF-8
ENV LANG el_GR.UTF-8
ENV LANGUAGE el_GR.UTF-8

RUN pip install --no-cache-dir --upgrade pip
#RUN pip install --no-cache-dir certifi

# Μονο ο neo4j driver χρειάζεται στο actions.py
RUN pip install --no-cache-dir neo4j==5.26.0
RUN pip install --no-cache-dir --upgrade requests
RUN pip install --no-cache-dir thefuzz
RUN pip install --no-cache-dir python-dotenv
RUN pip install --no-cache-dir PyYAML

# Υποτίθεται επιτρέπει μονο IPv4
#RUN echo 'precedence ::ffff:0:0/96 100' >> /etc/gai.conf

#copy everything in ./actions directory (your custom actions code) to /app/actions in container
COPY . /app/actions

# Ensure the .env file exists and is writable by the non-root user
RUN touch /app/actions/.env
RUN chown 1001:1001 /app/actions/.env
RUN chmod 664 /app/actions/.env

# Ensure the whole /app/actions directory is owned by user 1001
RUN chown -R 1001:1001 /app/actions

# Switch back to non-root to run code
USER 1001

CMD ["start", "--actions", "actions", "--cors", "*"]