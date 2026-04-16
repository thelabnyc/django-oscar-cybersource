FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:5e7e077145f451d6b8db8522b8b912ee318e2d074c6f64b8dce9248928517f00

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
