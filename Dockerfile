FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:a6afcc896aef58163c689a1a9df85eee9d0afeada446c641ca1e318770b1041f

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
