FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:6fda815489e617325dd05d760e511937dbc8521b86c14c59b3e781f9d12d9ee2

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
