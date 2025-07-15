FROM registry.gitlab.com/thelabnyc/python:3.13.820@sha256:c627949df95f50199db8ca6a44ab299970eaf30be6ddba2720936a4f6b923049

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
