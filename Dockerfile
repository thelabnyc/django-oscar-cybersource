FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:ffec4a4346c29efb891073411492115f111f13fe49acbec20a7f15e7947713d3

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
