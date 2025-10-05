FROM registry.gitlab.com/thelabnyc/python:3.13.989@sha256:b97d0877084de3375e06f5d71617535ded77f455bb22751295ba7ea6a47aeac3

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
