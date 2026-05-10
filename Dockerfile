FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:89144d9eefcfe1c3cc6866223c7de64ac824b1478f219a8e57a8e949c3765e86

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
