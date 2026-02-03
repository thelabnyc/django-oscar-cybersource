FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:3414114d6364b1b0d81c70a4d281b707a5e070aab66c7ed2f6bddf0db40960a8

RUN mkdir /code
WORKDIR /code

ADD ./Makefile .
RUN make system_deps && \
    rm -rf /var/lib/apt/lists/*

ADD . .
ENV PIP_NO_BINARY='lxml,xmlsec'
RUN uv sync

RUN mkdir /tox
ENV TOX_WORK_DIR='/tox'
