FROM node:20-alpine AS builder

WORKDIR /app

ARG VITE_API_BASE
ENV VITE_API_BASE=${VITE_API_BASE}

COPY package*.json ./

RUN npm ci

COPY . .

RUN npm run build

FROM node:20-alpine

WORKDIR /app

RUN npm install -g serve

COPY --from=builder /app/dist ./dist

EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "3000"]
