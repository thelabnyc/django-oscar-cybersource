FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:f1cf13a97a409df3de9b8d92a16636c7c0e8364458c95a82ccf29fcae95367fd

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
