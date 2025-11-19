FROM registry.gitlab.com/thelabnyc/python:3.13.1117@sha256:151affc6dd6abdfa22800baf2661e80f01e0f2a0573b9243e1c215c0c06cae1a

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
