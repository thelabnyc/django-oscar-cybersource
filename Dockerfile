FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:e77d57fcd66a0fe3a9ea39b7881add899ca5e48c87a7069414f9bf25689ffff4

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
