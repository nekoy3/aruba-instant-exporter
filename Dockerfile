FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY exporter/ exporter/

# Create a non-root user to run the exporter and adjust ownership
RUN useradd -m -u 10001 exporter && \
    chown -R exporter:exporter /app

USER exporter

EXPOSE 9877

ENTRYPOINT ["python", "-u", "-m", "exporter.main"]
