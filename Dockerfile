FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:2354b82ad0a5b313b7b1a774d20e2a67583b702a3e22f0009907833dedb63dca

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
