FROM registry.gitlab.com/thelabnyc/python:3.13.770@sha256:148b6fb07eb02bca3ffe2d658be4760fbd1f0c4d5955ea3f6e775f4d0c1e0426

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
