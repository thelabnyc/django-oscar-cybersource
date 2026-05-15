FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:0734df6eb93f45e426d5e308f61fb725d7b61ce04bce4ea572e0d826f9a9b01a

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
