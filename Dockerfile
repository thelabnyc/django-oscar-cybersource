FROM registry.gitlab.com/thelabnyc/python:3.13.902@sha256:bfd590d6602e7040089cdf64f5eaa0b376e6ee2a1b556a62db2392f92bc3ebf8

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
