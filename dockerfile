# syntax=docker/dockerfile:1
FROM alpine:3.23
RUN apk update && apk add musl-dev openssl-dev git python3-dev
WORKDIR /
RUN apk add py3-setuptools && git clone https://github.com/petertodd/python-bitcoinlib
WORKDIR /python-bitcoinlib
RUN python setup.py install
WORKDIR /
COPY src /src
CMD ["python", "/src/main.py"]