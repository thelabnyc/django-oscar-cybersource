FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:05dd808f5d674b15a9734645f5f1f1ed8f1eec89be5f51bae1a889cfb7b1bd18

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
