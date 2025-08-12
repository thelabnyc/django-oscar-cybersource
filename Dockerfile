FROM registry.gitlab.com/thelabnyc/python:3.13.896@sha256:f5436c83ac78f079c1e306e620604de76fdcab1b27bc7cefcfdaee3549308120

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
