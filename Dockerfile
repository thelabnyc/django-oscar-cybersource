FROM registry.gitlab.com/thelabnyc/python:3.13.680@sha256:13b2ea1750ff14bb8366fa5aa843d38d22cdf66e7c27b77d80bae082732ae045

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
