FROM registry.gitlab.com/thelabnyc/python:3.13.783@sha256:4f4509973f8d880e58df5b2828dafea0c690140580b4b519aec93b527e609ca4

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
