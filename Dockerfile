FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:8dee742000fbbad13dec9fb68c1d60d9da07aaab3aae2411a4fd952e8fdf3465

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
