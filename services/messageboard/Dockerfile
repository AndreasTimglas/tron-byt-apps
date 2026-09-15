FROM python:3.12-slim
WORKDIR /app
RUN useradd --system --uid 10001 board && mkdir /data && chown board /data
COPY server.py index.html style.css font.js layout.js app.js ./
USER board
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BOARD_DATA=/data/message.json
EXPOSE 8787
CMD ["python", "server.py"]
