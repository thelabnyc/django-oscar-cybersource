FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:e77427883c4da290469ad70cf23db3933ff3bbb3ec7cd4a8713c2b8bfebd5d14

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
