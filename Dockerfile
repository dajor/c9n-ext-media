# c9n extension "media": ffmpeg, Tesseract (de, en), poppler and qpdf behind a small HTTP service.
FROM python:3.12-slim-bookworm
ARG VERSION
LABEL org.opencontainers.image.title="c9n-ext-media" org.opencontainers.image.version=$VERSION app.c9n.extension.core_api="1"
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg poppler-utils qpdf tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
COPY server.py /app/server.py
# Same user as the c9n application, so files in the shared data volume stay readable for both.
RUN useradd --uid 10001 --create-home wirkivo && mkdir -p /data /state && chown wirkivo /state
USER wirkivo
WORKDIR /data
EXPOSE 9301
HEALTHCHECK --interval=10s --timeout=5s --retries=3 --start-period=10s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:9301/'+os.environ['C9N_EXT_TOKEN']+'/health',timeout=3)"
CMD ["python", "/app/server.py"]
