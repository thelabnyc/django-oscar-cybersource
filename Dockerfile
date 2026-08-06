FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:67f20539d69db7fd1d2bce180e2be647babbef7ab002a5f62dc05401fdc200d1

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
