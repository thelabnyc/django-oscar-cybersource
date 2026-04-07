FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:486864e4aaf15ecd905acf8c6f28ce8659a135f430d99cb9e2d84de5673dcb02

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
