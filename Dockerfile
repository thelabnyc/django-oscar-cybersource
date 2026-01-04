FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:8d4a409ba07ec0c890c0f96826329446ca6652e5bffb7ea1b8f92982c9946b7f

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
