FROM registry.gitlab.com/thelabnyc/python:3.13.1076@sha256:5f4eeaa01f98078d63ca24118ec05e808050da96cc8a4d488b7e72cc301684ca

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
