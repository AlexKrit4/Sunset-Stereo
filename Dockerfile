FROM node:22-alpine AS build
WORKDIR /app
COPY apps/sunset-stereo/package.json ./
RUN npm install
COPY apps/sunset-stereo/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY apps/sunset-stereo/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
