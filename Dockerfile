FROM registry.gitlab.com/thelabnyc/python:3.13.1107@sha256:7654d8fb58c03e8fc422ba2923f974536f4f393599031f158d84eb415a853a81

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
