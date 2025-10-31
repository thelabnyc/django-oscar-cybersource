FROM registry.gitlab.com/thelabnyc/python:3.13.1046@sha256:0dab50b681e3eed3cb989f0b1a015adf06646315e0c254b4e57f50f059d2d10e

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
