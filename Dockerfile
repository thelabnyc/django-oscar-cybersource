FROM registry.gitlab.com/thelabnyc/python:3.15@sha256:f193363cee93a158a846145943f9fdf8082da4d4debfebefe646d5eaa339df52

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
