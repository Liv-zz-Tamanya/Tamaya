# Tamanya 프론트 — 빌드(node) 후 정적 파일을 nginx로 서빙 + 백엔드 리버스 프록시.
# 1단계: Vite 빌드
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# API_BASE=/ → 같은 출처(same-origin) 상대경로로 호출 → CORS 불필요.
# nginx가 /api, /auth 를 백엔드로 프록시함.
ARG VITE_API_BASE=/
ARG VITE_AI_ENABLED=true
ENV VITE_API_BASE=$VITE_API_BASE \
    VITE_AI_ENABLED=$VITE_AI_ENABLED
RUN npm run build

# 2단계: nginx로 서빙
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
