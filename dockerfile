# syntax=docker/dockerfile:1
FROM alpine:3.23 AS build
WORKDIR /temp
RUN apk add --no-cache \
    build-base \
    git \
    autoconf \
    automake \
    libtool \
    openssl-dev \
    python3-dev \
    py3-pip


RUN git clone https://github.com/bitcoin-core/btcdeb/ \
    && cd btcdeb \
    && ./autogen.sh \
    && ./configure \
    && make clean \
    && make install

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN git clone https://github.com/petertodd/python-bitcoinlib \
    && cd python-bitcoinlib \
    && pip install --no-cache-dir .



FROM alpine:3.23
WORKDIR /app
RUN apk add --no-cache \
    libstdc++ readline python3 bash libssl3
COPY --from=build /usr/local/bin/btcc /usr/local/bin/btcc
COPY --from=build /usr/local/bin/btcc /usr/local/bin/btcdeb
COPY --from=build /usr/local/bin/btcc /usr/local/bin/tap
COPY --from=build /usr/local/bin/btcc /usr/local/bin/test-btcdeb
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY src /app/src
CMD ["python3", "/app/src/main.py"]
