FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:fe2254406f65d2933c9aa9751f9ec3007bc6e65e77bee8bbbf2b4e7bc8268aa0

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
