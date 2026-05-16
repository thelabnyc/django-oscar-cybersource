FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:8d4c636f6d0ef3fde8a6337e9add17b684664cc42fee5afb717f92abbe363cf9

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
