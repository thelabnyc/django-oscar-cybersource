FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:f0c48b89787a232cdcdab5905e2dda8372ca804d0d6cac7261ddd74aa24ddf47

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
