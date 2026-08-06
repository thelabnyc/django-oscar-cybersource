FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:45354efc7387d75964e168b7809b081b355b6f77748d36afa97e7cb6ed0e5735

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
