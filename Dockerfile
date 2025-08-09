FROM registry.gitlab.com/thelabnyc/python:3.13.894@sha256:c275cbd481ec30687d00ac0030129475b831e05dbb103644c10934723fc83228

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
