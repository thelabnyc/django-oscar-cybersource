FROM registry.gitlab.com/thelabnyc/python:3.15@sha256:f2be5893268aeaa0d74235d8861c16e1f5c85d8443a39cd06f8a73e9108a1d81

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
