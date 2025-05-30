FROM registry.gitlab.com/thelabnyc/python:3.13.719@sha256:bb4407fb7895ec7ddcb2eaa23dda805fc368e50b47934904efc254196be7975e

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
