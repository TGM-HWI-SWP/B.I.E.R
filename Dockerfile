FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir flask pymongo

EXPOSE 5000

CMD ["python", "-m", "src.lagerverwaltung.frontend.flask.gui"]
