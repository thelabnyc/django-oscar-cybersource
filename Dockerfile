FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:d8ebee6babbd2066d54414acdbc9dc68eb01a689691e1c15380b306ef1cfcc4e

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
