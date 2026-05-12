FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:8fe8a44cfb4a81b8e6706b7180c1c990f993c76e0736e509343ac8b3bafd6473

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
