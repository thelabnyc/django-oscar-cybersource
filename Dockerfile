FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:6a8ad5aa2ef732fa53a6364aeb781c76da796f333970d80207053e8a9d2c0009

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
