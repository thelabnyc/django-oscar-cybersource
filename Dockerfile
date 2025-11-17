FROM registry.gitlab.com/thelabnyc/python:3.13.1100@sha256:67eabf2e2dda0e5da618d3b6d9c20cde25cd37fed7183aaee3c9f37ee9696f97

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
