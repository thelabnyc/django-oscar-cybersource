FROM registry.gitlab.com/thelabnyc/python:3.13.974@sha256:a8e3c5425a167355846e94b7b32947b2795681f609f49a4d0c6ef326333045e1

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
