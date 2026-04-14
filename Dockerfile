FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:e95e7f0741c6eff85d9ab732bca05a5ef601e5165b7e6bbae3d78fa4111292bc

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
