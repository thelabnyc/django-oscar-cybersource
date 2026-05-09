FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:fc5e08ad337dd89402b10efce607f942646734d1f2cd559c3a97e4a52b289007

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
