FROM registry.gitlab.com/thelabnyc/python:3.15@sha256:5b1ae39e6c5d091331ff25e6c95de2b3d2531018efaec523b45ce5ae2de2c88c

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
