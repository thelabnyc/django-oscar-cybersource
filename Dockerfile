FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:71a092cc050bcfb3e795237c18521e964240331355ef059637a6a37b6bfffc3e

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
