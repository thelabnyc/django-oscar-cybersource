FROM registry.gitlab.com/thelabnyc/python:3.13.1037@sha256:d0c96677677557cc20143dcdccdcefe48dcc8ce01e9e68a0e42b901d2df67b5c

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
