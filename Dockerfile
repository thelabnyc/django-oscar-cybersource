FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:53a188bbf1876be398f0c0b7e44e85eba0aaddaf991c0e1be9b866a195e408df

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
