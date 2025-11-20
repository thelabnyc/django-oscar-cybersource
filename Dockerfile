FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:3ebff7128227829df9137429094aa25797479af9ffc8a86b68cdb8bcbf818492

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
