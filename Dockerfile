FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:780c091c3d03ac248b62966f4224d28ee73d8472c8784182ef260913b49c627e

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
