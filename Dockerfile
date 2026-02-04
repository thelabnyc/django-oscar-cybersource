FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:04def26a15dd439dd2b2109b335ea0f7bb22c92ca0ffc7025ed504309f395ea8

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
