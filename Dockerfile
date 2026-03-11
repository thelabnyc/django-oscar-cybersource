FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:81835b7f1ecd760ba76110b8ba6d9c7279e6941c886130fae8f82635363e87ba

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
