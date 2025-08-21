FROM registry.gitlab.com/thelabnyc/python:3.13.917@sha256:bc806413f1579754f48acb186f58cd446513089830de24a7ea1dd04e389094cd

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
