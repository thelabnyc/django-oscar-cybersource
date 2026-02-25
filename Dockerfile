FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:d3dae5607394565c6393500d7f59a9a0ba8bfacea17097df9ad5bcc6f75f2019

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
