FROM node:20-bullseye

WORKDIR /app

COPY package.json package-lock.json* /app/

# Install on container start (docker-compose command) for dev; keep image build fast.

COPY . /app

EXPOSE 5173
