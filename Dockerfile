FROM registry.gitlab.com/thelabnyc/python:3.13.1097@sha256:43ecc7c2173da19b4e14028fd8326d24cf3fbc6661b4892d53f37ea9f2ed2338

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
