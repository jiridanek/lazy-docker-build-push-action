ARG RUNTIME_BASE_IMAGE=runtime-base

FROM python:3.12.3-slim-bookworm as base

FROM base as builder

RUN apt-get update && \
    apt-get install --yes g++ build-essential

COPY requirements.txt requirements.txt

RUN python3 -m venv --without-pip /opt/venv
RUN pip --python /opt/venv install -r requirements.txt

FROM base as runtime-base

COPY --from=builder /opt/venv /opt/venv

FROM $RUNTIME_BASE_IMAGE as runtime

COPY src app

CMD /opt/venv/bin/python3 app/demo.py
