FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:c00ac3017c7dec33983899beb489d0ed9615861c9f61e86a2e8de65eca3bd3fc

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
