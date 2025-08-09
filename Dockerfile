FROM registry.gitlab.com/thelabnyc/python:3.13.892@sha256:7f2a493f9c96c6a8999c9f3f20499d5c2e3a191d6c506fb8f01ab50ec2197641

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
