FROM registry.gitlab.com/thelabnyc/python:3.13.662@sha256:e8cfdded2803e80be114029a669c10247a0825e97d0a3f77f482c5ce69d473c8

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
