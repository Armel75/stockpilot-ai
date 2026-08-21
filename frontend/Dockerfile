FROM node:20-alpine AS build
WORKDIR /app

# Réseau avec inspection TLS : le proxy injecte son certificat (chaîne incomplète)
# → npm ne peut pas vérifier le certificat de registry.npmjs.org.
# Désactivation de la vérification stricte pour ce build (local/Docker).
ENV NPM_CONFIG_STRICT_SSL=false

# Registre npm configurable (via --build-arg ou compose build args).
# Défaut : registre officiel. Miroir alternatif : https://registry.npmmirror.com
ARG NPM_REGISTRY=https://registry.npmjs.org
RUN npm config set registry "${NPM_REGISTRY}"

COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
