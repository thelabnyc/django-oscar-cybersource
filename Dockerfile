FROM registry.gitlab.com/thelabnyc/python:3.13.814@sha256:ee5123aacc61b94d89569ca1021a68e63b6fc0f2d20c36e81ee260db103c00f6

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
