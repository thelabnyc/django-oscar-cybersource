FROM registry.gitlab.com/thelabnyc/python:3.13.753@sha256:140aa7bd91defc376ebee6de730cf1c408ff52e8d78a8cbd605e8e14fb85a02e

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
