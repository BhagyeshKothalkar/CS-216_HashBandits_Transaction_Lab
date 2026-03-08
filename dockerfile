# syntax=docker/dockerfile:1
FROM alpine:3.23 AS build
RUN apk update && apk add musl-dev openssl-dev git python3-dev py3-setuptools py3-pip
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN git clone https://github.com/petertodd/python-bitcoinlib \
    && cd python-bitcoinlib \
    && pip install --no-cache-dir .

FROM alpine:3.23
WORKDIR /app
RUN apk add --no-cache python3 libssl3
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY src /app/src
CMD ["python3", "/app/src/main.py"]
