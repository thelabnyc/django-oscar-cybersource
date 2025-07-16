FROM registry.gitlab.com/thelabnyc/python:3.13.824@sha256:48e4bd65cf276fbee3e204628cb86d8cae85740db75d91ade350cf89ca50d867

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
