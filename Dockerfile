FROM registry.gitlab.com/thelabnyc/python:3.13.881@sha256:b42f98e7ab38e4d3e7dd2aed74ba35b225011c108e0f20a85720d7b43925be54

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
