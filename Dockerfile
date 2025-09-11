FROM registry.gitlab.com/thelabnyc/python:3.13.953@sha256:26eccf2e1c2660e741ef21979f2b1f28f06944ff2b82ce4d4edf7eb3a3af0070

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
