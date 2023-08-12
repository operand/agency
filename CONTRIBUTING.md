# Contributing

Thanks for considering contributing to the Agency library! Here's everything you
need to know to get started.

## Development Installation

```bash
git clone git@github.com:operand/agency.git
cd agency
poetry install
```

## Developing with the Demo Application

See [the demo directory](./examples/demo/) for instructions on how to run the
demo.

The demo application is written to showcase both native and AMQP spaces and
several agent examples. It can also be used for experimentation and development.

The application is configured to read the agency library source when running,
allowing library changes to be tested manually.

## Test Suite

Ensure you have Docker installed. A small RabbitMQ container will be
automatically created.

You can run the test suite with:

```bash
poetry run pytest
```

## Areas to Contribute

There are two general areas where you might want to contribute: examples, or the
core library.

### Adding to the Examples Directory

The [`examples/`](./examples/) directory is intended to be an informal directory
of example implementations, experiments, or ideas.

Feel free to add a folder under [`examples/`](./examples/) with anything you'd
like to share. It's unlikely to be rejected.

Please document it well enough for others to understand and please understand
that library maintainers will not maintain examples, except for the main `demo`
application. So if you want it kept up-to-date, that is up to you.

The main demo located at [`examples/demo/`](./examples/demo/) is maintained
closely with the core library. Feel free to copy the demo application as a basis
for your own examples or personal work. That's what it's for.

If you'd like to make significant changes to the main demo (not a simple bug fix
or something trivial), please discuss it with the maintainers.

### Core Library Contributions

Contributions to the core Agency library are encouraged as well, though expect
more scrutiny.

There isn't a complex process aside from opening a PR and having it approved by
maintainers, but other than bug fixes or trivial improvements, significant
changes to the core library should be discussed in order to ensure alignment on
design and implementation. If you're unsure, open an issue or discussion first.

A couple informal guidelines for core contributions:

* If you're adding functionality you should probably add new tests for it.

* Documentation should be updated or added as needed.
