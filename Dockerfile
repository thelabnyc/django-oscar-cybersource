FROM registry.gitlab.com/thelabnyc/python:3.13.900@sha256:c965dfcba6d1125f051c49437f39e8fbf382ed2412f4bc276d2fb0e947b6b225

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
