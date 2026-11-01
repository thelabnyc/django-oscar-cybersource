FROM registry.gitlab.com/thelabnyc/python:3.15@sha256:a04134afa4cc0bbde93cf357c2a1ffc8683590054a5cf99e1fa3eb929bb4aaa5

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
