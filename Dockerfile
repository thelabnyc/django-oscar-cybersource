FROM registry.gitlab.com/thelabnyc/python:py313@sha256:e1ed3aaeb702ac20c0340dcb09ae51d125738cabaa48516df73e98eb733fa91d

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
