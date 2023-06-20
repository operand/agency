# Set base image
FROM python:3.9

# Set working directory
WORKDIR /agency

# Copy pyproject.toml file
COPY pyproject.toml poetry.lock ./

# Install build dependencies
RUN pip install poetry

# Install project dependencies
RUN poetry install --no-dev

# Add application files
COPY . .

EXPOSE 8080
# Set runtime environment variables (if needed)

# Specify the startup command
CMD ["poetry", "run", "python", "demo.py"]
