FROM registry.gitlab.com/thelabnyc/python:3.13.735@sha256:e794ee002a1f245454759642987379928978a56245adffeab029edb8a23a032f

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
