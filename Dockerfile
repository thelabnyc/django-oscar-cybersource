FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:7d5bb832f68578fc6ae53d53dbaac23512500d1644d3a584f7ced66ecabd388d

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
