FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:7cb97eb739da0a5c29869fe63361427ce17abcf1059e4e9b83ae6142e83ede7a

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
