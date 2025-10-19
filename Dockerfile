FROM registry.gitlab.com/thelabnyc/python:3.13.1019@sha256:df99c5e2b35b6b6addec5d4d29599d0fb1585efc749f4860a0376aaa40a171f0

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
