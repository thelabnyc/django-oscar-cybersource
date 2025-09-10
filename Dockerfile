FROM registry.gitlab.com/thelabnyc/python:3.13.945@sha256:faebc49f1bedd576de24187d05e87ba3a7e64e7515ba19fba209821703e3ff7b

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
