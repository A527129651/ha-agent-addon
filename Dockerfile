ARG BUILD_FROM
FROM $BUILD_FROM
RUN apk add --no-cache python3 py3-pip
WORKDIR /app
COPY backend/requirements.txt .
RUN pip3 install --break-system-packages -r requirements.txt
COPY backend/ ./backend/
COPY frontend/ ./frontend/
RUN mkdir -p /etc/services.d/ha_agent
COPY s6/run /etc/services.d/ha_agent/run
COPY s6/finish /etc/services.d/ha_agent/finish
RUN chmod a+x /etc/services.d/ha_agent/run /etc/services.d/ha_agent/finish
EOFcat > /config/addons/ha_agent/Dockerfile << 'EOF'
ARG BUILD_FROM
FROM $BUILD_FROM
RUN apk add --no-cache python3 py3-pip
WORKDIR /app
COPY backend/requirements.txt .
RUN pip3 install --break-system-packages -r requirements.txt
COPY backend/ ./backend/
COPY frontend/ ./frontend/
RUN mkdir -p /etc/services.d/ha_agent
COPY s6/run /etc/services.d/ha_agent/run
COPY s6/finish /etc/services.d/ha_agent/finish
RUN chmod a+x /etc/services.d/ha_agent/run /etc/services.d/ha_agent/finish
