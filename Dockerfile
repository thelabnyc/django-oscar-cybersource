FROM registry.gitlab.com/thelabnyc/python:3.15@sha256:91a187daf0ba3c402d459ffec8188f8c1ea1b8dfa347a952f8baffdbdfab8eaf

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
