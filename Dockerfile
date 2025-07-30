FROM registry.gitlab.com/thelabnyc/python:3.13.875@sha256:cdf74024a742395ae2a13234e0adfd553b8a42eb1b5b8ed85f55f0b5ad4c5e33

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
