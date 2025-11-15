FROM registry.gitlab.com/thelabnyc/python:3.13.1093@sha256:40725ea7ae96d37d314339812d78e5b9a4c642f6e4e58c7385b3621d8c743568

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
