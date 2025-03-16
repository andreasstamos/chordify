FROM debian:12

RUN apt update
RUN apt install -y nginx python3.11-venv

RUN ln -s /etc/nginx/sites-available/chordify /etc/nginx/sites-enabled/chordify

RUN mkdir -p /usr/src/chordify

WORKDIR /usr/src/chordify

ENV VIRTUAL_ENV=/usr/src/chordify/venv
RUN python3 -m venv $VIRTUAL_ENV
RUN $VIRTUAL_ENV/bin/pip install --upgrade pip
COPY ./requirements.txt .
RUN $VIRTUAL_ENV/bin/pip install --no-cache-dir --upgrade -r requirements.txt

COPY docker/node/nginx_chordify /etc/nginx/sites-available/chordify

COPY . .

RUN rm /etc/nginx/sites-enabled/default

CMD ["./docker/node/start_manager.sh"]

