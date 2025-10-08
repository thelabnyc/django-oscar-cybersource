FROM registry.gitlab.com/thelabnyc/python:3.13.997@sha256:0783ea45da45382080c1dfea3cc8fd3507d2100ad1e0c1ef944e100713b58642

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
