FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:6cdb4e05476fc9bd434686605fb9662df60df7cb308426aba5cd4a4e276d7181

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
