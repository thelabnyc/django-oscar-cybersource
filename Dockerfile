FROM registry.gitlab.com/thelabnyc/python:3.13.796@sha256:97272ff540e49903a88f1e03e3d16f0dd7ad71fe4801d9e4c4358509da2517f6

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
