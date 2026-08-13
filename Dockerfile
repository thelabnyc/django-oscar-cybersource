FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:235a2ecc28a9852fd55e582cb8142c94d11064d622bb98b64e75544871ed4366

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
