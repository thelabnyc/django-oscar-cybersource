FROM registry.gitlab.com/thelabnyc/python:3.13.810@sha256:a1bdc5490a42db1600428af3ac25a0582f28bafb412179340234dc495ab12070

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
