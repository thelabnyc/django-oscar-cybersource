FROM registry.gitlab.com/thelabnyc/python:py313@sha256:f66034dd9cb8e03d350cf81b6fba002f8241a1640d525ad1f77b6f3374e1c47b

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
