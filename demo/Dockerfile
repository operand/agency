# Set base image
FROM python:3.9 as base

# Update and install build dependencies
RUN apt-get update && \
    apt-get upgrade -y \
    # node dependencies
    curl \
    gnupg \
    lsb-release

RUN pip install setuptools wheel poetry
ENV POETRY_VIRTUALENVS_PATH=/venv

# Install agency dependencies
FROM base as agency_deps
WORKDIR /agency
COPY ./pyproject.toml ./poetry.lock /agency/
RUN poetry install --no-root

# Install demo dependencies without full agency source
FROM base as demo_deps
WORKDIR /agency
COPY --from=agency_deps /venv /venv
COPY demo/pyproject.toml demo/poetry.lock ./demo/
COPY pyproject.toml poetry.lock README.md ./
COPY agency/__init__.py ./agency/__init__.py
RUN cd demo && poetry install

# Build agency-js
FROM base as agency_js_build
WORKDIR /agency-js
RUN curl -sL https://deb.nodesource.com/gpgkey/nodesource.gpg.key | gpg --dearmor | tee /etc/apt/trusted.gpg.d/nodesource.gpg > /dev/null && \
    echo "deb https://deb.nodesource.com/node_18.x $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs && \
    npm install -g yarn
COPY agency-js/package.json agency-js/yarn.lock ./
RUN yarn install
COPY agency-js/ ./
RUN yarn build

# Build demo
FROM base
WORKDIR /agency/demo
COPY --from=demo_deps /venv /venv
COPY --from=agency_js_build /agency-js/dist /agency-js-dist
COPY . .

# Go
CMD ["python", "main.py"]
