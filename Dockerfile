FROM registry.gitlab.com/thelabnyc/python:3.13.660@sha256:d1a36f578df6b7eea0cb17bc35770a8aec3f86484bfd7bc5afc31255fc0d9ceb

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
