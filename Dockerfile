FROM registry.gitlab.com/thelabnyc/python:py313@sha256:6a8762e21fdb1daa3152d5bff2d4a9e1d2a8e438f5ac352f50b15629c01e0db3

RUN mkdir /code
WORKDIR /code

ADD ./Makefile .
RUN make system_deps && \
    rm -rf /var/lib/apt/lists/*

ADD . .
ENV POETRY_INSTALLER_NO_BINARY='lxml,xmlsec'
ENV PIP_NO_BINARY='lxml,xmlsec'
RUN poetry install

RUN mkdir /tox
ENV TOX_WORK_DIR='/tox'
