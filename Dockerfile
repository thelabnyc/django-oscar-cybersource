FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:69e37e1668070251e454860ca363c094696f3f11ee803f577efdf04359abb9ee

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
