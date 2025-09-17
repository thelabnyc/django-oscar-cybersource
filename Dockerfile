FROM registry.gitlab.com/thelabnyc/python:3.13.961@sha256:2c96555191b14909c223e9767ae4f8bb420b3aab0c9452408279947340089c34

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
