FROM registry.gitlab.com/thelabnyc/python:3.13.785@sha256:feac423f8bdec4aa2c0f43584910a7f51c8c0ec435d8958a875d6a7ad70e8799

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
