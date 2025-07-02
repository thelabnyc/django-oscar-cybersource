FROM registry.gitlab.com/thelabnyc/python:3.13.789@sha256:8653d069ee80c0d104143560eb826916ccaaa6f1a42640b180d4d67d8bcd09c9

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
