FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:76797136d2537ab993cfd4d409ac1b1ef963c9d998a907c6c5e272abd3917c8b

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
