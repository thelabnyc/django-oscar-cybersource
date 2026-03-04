FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:7d5e109bb4042efc7418b423c029585d511ac9acf4c75475df40db2ea9caf1ef

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
