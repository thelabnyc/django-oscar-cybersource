FROM registry.gitlab.com/thelabnyc/python:3.13.826@sha256:26de8aad748da74ff4390fdbde3e04da0109f9275a0cbce1ea05ffdaedb6a719

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
