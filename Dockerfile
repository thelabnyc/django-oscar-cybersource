FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:d5f5e272767535d07a13c8a817760e0c42f72e61df42c8378fddb89eedaccebc

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
