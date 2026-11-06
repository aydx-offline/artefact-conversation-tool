FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ca ca
COPY data data
COPY cases cases

CMD ["python", "-m", "ca", "--help"]
