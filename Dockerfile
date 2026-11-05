FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ca ca
COPY web web
COPY data data
COPY cases cases

ENV CA_WEB_HOST=0.0.0.0
EXPOSE 8765

CMD ["python", "-m", "ca.web"]
