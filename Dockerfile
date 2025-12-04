FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:ddb71bc5cd982178418dc0186804796b0780b552d815ed5213bd520110b35103

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
