FROM registry.gitlab.com/thelabnyc/python:3.13.860@sha256:ff95b4a51e864a87c37a2af6b61f4737071dc7cfab215040370f51637991b844

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
