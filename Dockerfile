FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:1c2dce98d4f424414f0d80ba890060a609d6487b5806717539407bdd817ff3c4

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
