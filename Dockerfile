FROM registry.gitlab.com/thelabnyc/python:3.13.913@sha256:410dfe97acd97150824e7e721ca614e2d448608746ea6ad780c0bec26fb7e2d0

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
