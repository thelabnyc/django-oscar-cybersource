FROM registry.gitlab.com/thelabnyc/python:3.13.828@sha256:7b95840c3577ee0e370971ff25aff2fceb82661a1b652ae7b4d3368deb3ecb05

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
