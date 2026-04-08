FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:d0e7e3895e1e3c269cb56687664513a51dae0b86c22b1524c6d5332327bb8c6d

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
