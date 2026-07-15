FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:c85a264b8085b45ee2eb31c2cdffa84fa3f013cfe36a0950391268715e0357af

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
