FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

EXPOSE 5000

CMD ["sh", "-c", "python -m bierapp.db.init.setup && python -m bierapp.db.init.seed && python -m bierapp.frontend.flask.gui"]
