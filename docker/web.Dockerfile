FROM node:20-alpine AS build
WORKDIR /app
COPY kiarsy-web/package*.json ./
RUN npm ci
COPY kiarsy-web/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
# Angular 19 often outputs to dist/kiarsy-web/browser — adjust if needed after first build
COPY --from=build /app/dist/kiarsy-web/browser /usr/share/nginx/html
EXPOSE 80
