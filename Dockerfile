FROM registry.gitlab.com/thelabnyc/python:3.13.873@sha256:5af51d7e1e7d5608bb0bb84e598227995784b6c6e073575fac49aa06b131e1e8

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
