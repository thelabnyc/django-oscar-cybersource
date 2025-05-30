FROM registry.gitlab.com/thelabnyc/python:3.13.713@sha256:8d7c4daab9d885ab727d71bb823440f25f0f67dbf1d6966228cb08f23abd9a1e

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
