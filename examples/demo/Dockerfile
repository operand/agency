# Set base image
FROM python:3.9 as base

# Update system
RUN apt-get update && apt-get upgrade -y

WORKDIR /agency

# Install build dependencies
RUN pip install setuptools wheel poetry
ENV POETRY_VIRTUALENVS_PATH=/venv

# Install agency dependencies
FROM base as agency_deps
COPY ./pyproject.toml ./poetry.lock /agency/
RUN poetry install --no-root

# Install demo app dependencies
FROM base as demo_deps

# Copy venv from agency_deps stage
COPY --from=agency_deps /venv /venv

# Install demo dependencies without full agency source
COPY examples/demo/pyproject.toml examples/demo/poetry.lock ./examples/demo/
COPY pyproject.toml poetry.lock README.md ./
COPY agency/__init__.py ./agency/__init__.py
RUN cd examples/demo && poetry update && poetry install

# Build demo image
FROM base

# Copy venv from demo_deps stage
COPY --from=demo_deps /venv /venv

# Copy full source
COPY . .

# Go
WORKDIR /agency/examples/demo
CMD ["python", "demo_threaded.py"]
