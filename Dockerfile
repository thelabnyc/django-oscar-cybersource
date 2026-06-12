FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:75cd1c824ad6b44766517ca11866a375c2a1983a5e1963b04ad56adc986fef69

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
