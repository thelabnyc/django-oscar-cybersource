FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:f5a1606f6658319d52713d05d44e2f9ac4bb63346fd8766d2981e3d2697bc370

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
