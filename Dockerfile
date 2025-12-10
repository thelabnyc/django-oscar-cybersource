FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:e6c45ffbb3891328f4689c29f998d5bee2257708cea2709df93bf91b1fac0817

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
