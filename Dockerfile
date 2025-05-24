FROM registry.gitlab.com/thelabnyc/python:3.13.707@sha256:379ebd0f299bf4cf64c5c0c829afebe3b622aae78f02fcc04d779488e330b8ff

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
