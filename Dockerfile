FROM registry.gitlab.com/thelabnyc/python:3.13.671@sha256:54aa7c9bf855f374a648d67bb1444575634f54cdd73517f93afb728b6963e5be

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
