FROM registry.gitlab.com/thelabnyc/python:3.13.978@sha256:71703915e944ea7f01de89cbd2e58d514aed38dbbfbdc3fc6ca9da3c57bcb096

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
