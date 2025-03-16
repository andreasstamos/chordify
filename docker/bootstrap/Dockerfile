# builder
FROM node:lts-alpine AS builder

WORKDIR /usr/src/app

COPY frontend/package.json .
COPY frontend/package-lock.json .
RUN npm ci
COPY frontend/ .
COPY docker/bootstrap/Config.js src/config/Config.js
RUN npm run build

# final

FROM debian:12

RUN apt update
RUN apt install -y nginx python3.11-venv

RUN mkdir /etc/nginx/ssl
RUN openssl req -x509 -nodes -days 36500 -newkey rsa:4096\
	    -keyout /etc/nginx/ssl/nginx.key \
	    -out /etc/nginx/ssl/nginx.crt \
	    -subj "/CN=localhost"

RUN mkdir -p /usr/src/chordify
WORKDIR /usr/src/chordify

ENV VIRTUAL_ENV=/usr/src/chordify/venv
RUN python3 -m venv $VIRTUAL_ENV
RUN $VIRTUAL_ENV/bin/pip install --upgrade pip
COPY ./requirements.txt .
RUN $VIRTUAL_ENV/bin/pip install --no-cache-dir --upgrade -r requirements.txt

RUN ln -s /etc/nginx/sites-available/chordify /etc/nginx/sites-enabled/chordify
RUN rm /etc/nginx/sites-enabled/default
COPY docker/bootstrap/ffdhe2048.txt /etc/nginx/ssl/ffdhe2048.txt
COPY docker/bootstrap/nginx_chordify /etc/nginx/sites-available/chordify

COPY docker/bootstrap/htpasswd /etc/apache2/.htpasswd

COPY --from=builder /usr/src/app/build /usr/share/nginx/html/chordify

COPY . .

CMD ["./docker/bootstrap/start_manager.sh"]

