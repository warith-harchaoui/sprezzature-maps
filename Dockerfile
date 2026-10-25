FROM python:3.12-slim

WORKDIR /app

COPY . .

# Both this package and sprezzature-figures are on PyPI, so pip resolves the
# dependency on its own. This used to apt-get git and clone the sibling repo,
# with a comment asserting "neither is on PyPI yet" — true when written, false
# since, and the workaround outlived it: an extra apt layer, and a dependency
# pinned to whatever HEAD happened to be at build time, which is the opposite
# of a reproducible image.
#
# Not editable: an image has no source tree to edit. The generators ship as
# the packaged `sprezzature_maps_scripts`, so a plain install carries them.
RUN pip install --no-cache-dir ".[cli,api,mcp]"

EXPOSE 8000

# Serve the thing the image was built with. The previous default printed a
# `--help` message and exited, which is a container that does nothing: this
# image carries the HTTP API, the MCP surface and the GUI gallery, so the
# useful default is to run them. Override with any of the CLIs:
#
#   docker run --rm -v "$PWD:/out" IMAGE make-map choropleth --out /out/world.svg
CMD ["uvicorn", "sprezzature_maps.api:app", "--host", "0.0.0.0", "--port", "8000"]
