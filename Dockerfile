FROM python:3.12-slim
WORKDIR /app
COPY agent/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt
