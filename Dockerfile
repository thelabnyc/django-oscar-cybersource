FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:4aeb672252d3dc65f3f55ab6114bf5df1d08a9e3f7ea64f671e2b4622261cb01

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
