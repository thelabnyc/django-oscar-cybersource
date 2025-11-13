FROM registry.gitlab.com/thelabnyc/python:3.13.1086@sha256:ba6afe926a1e3f876cadde3752e7bb43ff5978deab7b9ee0bd22c4f822554dd6

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
