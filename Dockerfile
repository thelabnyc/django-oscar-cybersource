FROM registry.gitlab.com/thelabnyc/python:3.13.698@sha256:45837b7e9a90c6d58e0f42dc89c42b1bdd52f406f07a07fa54207918249c027c

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
