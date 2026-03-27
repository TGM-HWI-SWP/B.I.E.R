FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app/src

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir flask pymongo psycopg2-binary requests

EXPOSE 5000

CMD ["python", "-m", "bierapp.frontend.flask.gui"]
