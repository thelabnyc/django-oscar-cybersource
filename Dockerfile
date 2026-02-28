FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:c63eea6a970e5e36dec447435f3ba010db753e90eed65feec23b00e4f00caec8

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
