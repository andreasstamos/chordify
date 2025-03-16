FROM python:3

WORKDIR /usr/src/app

COPY cli/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN apt update
RUN apt install -y inetutils-ping

COPY cli/. .
COPY docker/benchmark/configuration.py configuration.py

CMD [ "./benchmark.py" ]

