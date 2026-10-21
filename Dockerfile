FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:9a9f865840d4ce0ddbc177555d64cadc13b51b3d51908a502a386c24aaef18dc

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
