FROM registry.gitlab.com/thelabnyc/python:3.13.980@sha256:688deebef90fe9a3d151fb15656be0f6e0026970e009f208d104fac56373b5d0

RUN mkdir /code
WORKDIR /code

ADD ./Makefile .
RUN make system_deps && \
    rm -rf /var/lib/apt/lists/*

ADD . .
ENV PIP_NO_BINARY='lxml,xmlsec'
RUN uv sync

RUN mkdir /tox
ENV TOX_WORK_DIR='/tox'
