FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:e8ffa572205957943ce5300c6ffca236b6dae7de2e2959d6f7d758c6b938aabc

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
