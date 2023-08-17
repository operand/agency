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

These are the general areas where you might want to contribute:

### The Examples Directory

The [`examples/`](./examples/) directory is intended to be an informal directory
of example implementations or related sources.

Feel free to add a folder under [`examples/`](./examples/) with anything you'd
like to share. Please add a README file if you do.

Library maintainers will not maintain examples, except for the main `demo`
application. So if you want it kept up-to-date, that is up to you.

The main demo located at [`examples/demo/`](./examples/demo/) is maintained with
the core library. Feel free to copy the demo application as a basis for your own
examples or personal work.

If you'd like to make significant changes to the main demo (not a bug fix or
something trivial), please discuss it with the maintainers.

### Core Library Contributions

Contributions to the core library are appreciated as well. There isn't a complex
process. Just open a PR and have it approved.

Anything other than bug fixes or trivial improvements should be discussed in
order to ensure alignment on design and implementation. If you're unsure, open
an issue or discussion first, or reach out on discord.

A couple informal guidelines for core contributions:

* If you're adding functionality you should probably add new tests for it.
* Documentation should be updated or added as needed.


### Maintaining Documentation

Documentation is hosted at https://createwith.agency. The source for the help
site is maintained in the [`site/`](./site/) directory.

The help site uses the [Jekyll](https://jekyllrb.com/) static site generator
along with the [GitHub Pages](https://pages.github.com/) service to host the
site. Ruby dependencies are defined using Bundler (Gemfile).

The help site includes two kinds of documentation:

#### Articles

Articles are located at [`site/articles/`](./site/articles/). Feel free to update or
add new articles as needed.

#### API Documentation

API documentation is generated automatically using [pdoc](https://pdoc.dev/).
Any docstrings that are defined in the codebase will be included in the API
documentation.
