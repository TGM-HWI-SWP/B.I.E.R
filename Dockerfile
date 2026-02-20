FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir gradio pymongo

EXPOSE 7860

CMD ["python", "-m", "src.ui.gui"]
