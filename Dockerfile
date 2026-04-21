FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:6db2f911d10c60552bf159f511e709d40c2a37b02166f7c7e19058f6987ab60b

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
