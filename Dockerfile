FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:ff0925a3cf7646879698ab3548a258e81c50ef1d88b771e165b55c3a467a4d55

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
