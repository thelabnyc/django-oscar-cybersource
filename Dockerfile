FROM registry.gitlab.com/thelabnyc/python:3.13.929@sha256:4a624777eb546e355c4287fb56b89466be1e8ce74e1a25e9d760acb1b902bfef

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
