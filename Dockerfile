FROM registry.gitlab.com/thelabnyc/python:3.15@sha256:967e7350758d4e74633c1e4e69715abc20335ac57882886b9aef27c57f208f96

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
