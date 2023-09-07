# https://createwith.agency

This directory contains source files and content for the Agency website. This
page contains instructions for how to update the site.

## Updating Articles

Articles are written in Markdown and located at [`_articles/`](./_articles/).
Feel free to update or add new articles as needed.

## Updating API Documentation

API documentation is generated automatically using [pdoc](https://pdoc.dev/).

Any docstrings that are defined in the codebase will be included in the API
documentation. You should follow the [Google Style
Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).

To regenerate the API documentation locally, run:

```bash
rm -rf _api_docs/
poetry run pdoc ../agency \
  --template-directory ./pdoc_templates \
  --docformat google \
  --output-dir _api_docs
```


## Updating the Website

The site uses the [Jekyll](https://jekyllrb.com/) static site generator with the
[Just the Docs](https://just-the-docs.com/) theme. Hosting is on [GitHub
Pages](https://pages.github.com/). Ruby dependencies are defined using Bundler
(Gemfile).

To install and run the website locally:

- Install Ruby (see [.ruby-version](./.ruby-version) for the necessary version).
- Run:
  ```bash
  gem install bundler
  bundle install
  ./devserver # regenerates and runs the website
  ```
- Open [http://localhost:4000](http://localhost:4000) in your browser.
