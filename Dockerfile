FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:dcfb264c5af270ea52ae5b71fc84acd78cd3ac7f9b31de2e94eb56b9104c27c6

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
