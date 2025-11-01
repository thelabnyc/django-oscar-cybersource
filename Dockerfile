FROM registry.gitlab.com/thelabnyc/python:3.13.1052@sha256:aaec4c649afd817c6a2d8b492c7cb0d7fdd4f416ec9494d9ed451333cabcb4e0

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
