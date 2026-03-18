FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:ab831a06a29a37bb133444e7f151563f4e0f5e2caf23359cd8076a09be5a510c

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
