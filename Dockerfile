FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:0e41570605a9add60854b464b5d6af7f367406efc2ee75e6a222da7d3f03d390

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
