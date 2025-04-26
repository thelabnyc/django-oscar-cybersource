FROM registry.gitlab.com/thelabnyc/python:py313@sha256:a6d6a1b7ca377cd1a8e96e09dd93791cf3929675d7ec1d0ea9dce9177bfc1b1e

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
