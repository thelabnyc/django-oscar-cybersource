FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:e2ac4f67885cdc31c2602ff500eb2574c5d847c9b44e73c796dc7b31a8a3f98a

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
