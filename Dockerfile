FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:9da1a4428f7ad88f23bf8200566cc061a6b1c39d6fcb7cb51b4f0fcce8ca16c2

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
