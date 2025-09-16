FROM registry.gitlab.com/thelabnyc/python:3.13.957@sha256:db0566fc8c17a188cd079238813ae6df4010c7fa586f4fefcfa8c4bd34c0acfb

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
