FROM registry.gitlab.com/thelabnyc/python:3.13.906@sha256:f97651dee648b4fa1a5da9beb7d7410dadcd96d68a5bf7bcb08ef56e1b3cfa21

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
