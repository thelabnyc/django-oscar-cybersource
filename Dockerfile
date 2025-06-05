FROM registry.gitlab.com/thelabnyc/python:3.13.730@sha256:48ead35b07386d36b46420c486875cc8448690219158fd92f221546a6d4d4245

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
