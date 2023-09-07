# Contributing

Thanks for considering contributing to the Agency library! Here's everything you
need to know to get started.

If you have any questions or want to discuss something, please open an
[issue](https://github.com/operand/agency/issues) or
[discussion](https://github.com/operand/agency/discussions) or reach out on
[discord](https://discord.gg/C6F6245z2C).

## Development Installation

```bash
git clone git@github.com:operand/agency.git
cd agency
poetry install
```

## Developing with the Demo Application

See [the demo directory](./examples/demo/) for instructions on how to run the
demo.

The demo application is written to showcase the different space types and
several agent examples. It can also be used for experimentation and development.

The application is configured to read the library source when running, allowing
library changes to be tested manually.

## Test Suite

Ensure you have Docker installed. A small RabbitMQ container will be
automatically created by the test suite.

You can run the tests:

```bash
poetry run pytest
```

## Areas to Contribute

These are the general areas where you might want to contribute:

### The Examples Directory

The [`examples/`](./examples/) directory is intended to be an informal directory
of example implementations or related sources.

Feel free to add a folder under [`examples/`](./examples/) with anything you'd
like to share. Please add a README file if you do.

Library maintainers will not maintain examples, except for the main `demo`
application. So if you want it kept up-to-date, that is up to you, but don't
feel obligated.

The main demo located at [`examples/demo/`](./examples/demo/) is maintained with
the core library. Feel free to copy the demo application as a basis for your own
examples or personal work.

If you'd like to make significant changes to the main demo (not a bug fix or
something small), please discuss it with the maintainers.

### Core Library Contributions

There isn't a complex process to contribute. Just open a PR and have it
approved.

For significant library changes (not bug fixes or small improvements) please
discuss it with the maintainers in order to ensure alignment on design and
implementation.

Informal guidelines for core contributions:

* If you're adding functionality you should probably add new tests for it.
* Documentation should be updated or added as needed.

### Maintaining Documentation

Documentation is hosted at https://createwith.agency. The source for the help
site is maintained in the [`site/`](./site/) directory. Please see that
directory for information on editing documentation.
