FROM registry.gitlab.com/thelabnyc/python:3.13.1034@sha256:e664163a34766cf7d1cd257b8abc9dfcfc3e03f562808e5f675d108f798f5c0f

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
