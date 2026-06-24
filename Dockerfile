ARG BUILD_FROM
FROM $BUILD_FROM
RUN apk add --no-cache python3 py3-pip
WORKDIR /app
COPY backend/requirements.txt .
RUN pip3 install --break-system-packages -r requirements.txt
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY rootfs/ /
RUN chmod +x /usr/bin/run.sh
CMD ["/usr/bin/run.sh"]
