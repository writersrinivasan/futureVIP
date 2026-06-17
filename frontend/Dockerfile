# ──────────────────────────────────────────────────────────────
#  FUTURE VIP — Frontend Dockerfile
#  Multi-stage build: development + production targets
# ──────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────
#  Stage 1: Dependencies (shared cache layer)
# ──────────────────────────────────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app

# Install dependencies separately for better layer caching
COPY package.json package-lock.json* ./
RUN npm ci --prefer-offline

# ──────────────────────────────────────────────────────────────
#  Stage 2: Development Server
# ──────────────────────────────────────────────────────────────
FROM node:20-alpine AS development

WORKDIR /app

# Copy installed node_modules from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy source (will be overridden by volume mount in docker-compose)
COPY . .

EXPOSE 3000

ENV NODE_ENV=development

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget -q --spider http://localhost:3000 || exit 1

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]

# ──────────────────────────────────────────────────────────────
#  Stage 3: Builder (production build)
# ──────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy deps
COPY --from=deps /app/node_modules ./node_modules

# Copy source files
COPY . .

# Build production bundle
ARG VITE_API_URL
ARG VITE_WS_URL
ARG VITE_APP_VERSION

ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_WS_URL=${VITE_WS_URL}
ENV VITE_APP_VERSION=${VITE_APP_VERSION}
ENV NODE_ENV=production

RUN npm run build

# Verify build output exists
RUN test -d /app/dist || (echo "Build failed: dist/ not found" && exit 1)

# ──────────────────────────────────────────────────────────────
#  Stage 4: Production Runner (nginx:alpine serves static files)
# ──────────────────────────────────────────────────────────────
FROM nginx:1.25-alpine AS production

LABEL maintainer="FutureVIP Team <dev@futurevip.ai>"
LABEL description="React SPA static file server for FUTURE VIP"

# Install curl for healthcheck
RUN apk add --no-cache curl

# Remove default nginx site
RUN rm -f /etc/nginx/conf.d/default.conf

# Create nginx site config for SPA (handles client-side routing)
RUN cat > /etc/nginx/conf.d/futurevip.conf << 'EOF'
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Cache static assets aggressively
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
    }

    # index.html: never cache (for cache busting on deploy)
    location = /index.html {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        expires 0;
    }

    # SPA fallback: all routes serve index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Health check endpoint (used by nginx upstream and orchestrators)
    location /health {
        access_log off;
        return 200 'OK';
        add_header Content-Type text/plain;
    }

    # Disable serving hidden files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml image/svg+xml;
    gzip_comp_level 6;
}
EOF

# Copy build output from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

STOPSIGNAL SIGQUIT

CMD ["nginx", "-g", "daemon off;"]
