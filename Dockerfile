FROM registry.gitlab.com/thelabnyc/python:3.13.1040@sha256:b26794a7f8e0f1d82448795594a4ca747a98ca128626164f0a05603187132a5c

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
