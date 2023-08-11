# Contributing

There are two high level areas where you might want to contribute: examples, or
the core library itself.


## Adding to the Examples Directory

The [`examples/`](./examples/) directory is intended to be an informal directory
of example implementations, experiments, or ideas.

Feel free to add a folder under the [`examples/`](./examples/) directory with
anything you'd like to share. It's unlikely to be rejected.

Please document it well enough for others to understand and please make an
effort to maintain it if possible. Library maintainers will not be responsible
for maintaining examples, except for the main `demo` application.

The main demo located at [`examples/demo/`](./examples/demo/) is maintained
closely with the core library, so if you'd like to make significant changes to
it (not a simple change or bug fix for example), please discuss this first. But
feel free to copy the demo application as a basis for your own examples or
personal work.


## Core Library Contributions

Contributions to the core Agency library itself are encouraged as well, though
expect more scrutiny.

There isn't a formal process yet aside from opening a PR and having it reviewed
by maintainers, but other than bug fixes or small improvements, significant
changes to the core library should be discussed in order to ensure alignment on
design and implementation. If you're unsure, open an issue first to discuss.

A couple informal guidelines for core contributions:

* Tests should be updated or added with any core changes. If you're adding
  functionality there should be new tests for it.

* Documentation should be updated or added as needed.
