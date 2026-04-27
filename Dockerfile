FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:5e79e7662259f4d0c0ccceebaf193d710e9cac99205f33ea347d0c180ce18fc5

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
