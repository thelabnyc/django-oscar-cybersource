FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:5d5275a8a69bbcaa3ff858d8201c199985ee6b85c8d05a1c9c58d056f2240df0

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
