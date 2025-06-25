FROM registry.gitlab.com/thelabnyc/python:3.13.766@sha256:281d5d17fa4c1b41c70ec718cb8991c32730d36ccbbb817601254e648c498b04

RUN mkdir /code
WORKDIR /code

ADD ./Makefile .
RUN make system_deps && \
    rm -rf /var/lib/apt/lists/*

ADD . .
ENV POETRY_INSTALLER_NO_BINARY='lxml,xmlsec'
ENV PIP_NO_BINARY='lxml,xmlsec'
RUN poetry install

RUN mkdir /tox
ENV TOX_WORK_DIR='/tox'
