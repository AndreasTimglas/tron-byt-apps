FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*
RUN useradd --system --uid 10001 board && mkdir /data && chown board /data
COPY gifstore.py gifs.html gifs.js scheduling.py server.py index.html style.css font.js layout.js app.js flowers.html flowers.js ./
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
USER board
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BOARD_DATA=/data/message.json
EXPOSE 8787
CMD ["python", "server.py"]
