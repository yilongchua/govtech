FROM python:3.11-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY main.py /app/main.py
COPY backend /app/backend
COPY scripts /app/scripts
COPY config.yaml /app/config.yaml
COPY 2174_y26_sy.pdf /app/2174_y26_sy.pdf
COPY 2174_y26_sy.md /app/2174_y26_sy.md

EXPOSE 8000

CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "8000"]


FROM node:20-alpine AS frontend-build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend ./
RUN npm run build


FROM nginx:1.27-alpine AS frontend

COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
