FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:7905ebab6491a567240c1780aa60583b0ec5ccb2334ab4ac5e61f7809699344a

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
