FROM python:3

WORKDIR /usr/src/app

COPY cli/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY cli/. .
COPY docker/cli/configuration.py configuration.py

CMD [ "./cli.py" ]

