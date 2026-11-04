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
RUN pip install --no-cache-dir "."

EXPOSE 8000

# Serve the thing the image was built with. The previous default printed a
# `--help` message and exited, which is a container that does nothing. The
# default serves the HTTP API and the gallery page at `/`. It does NOT serve
# the MCP endpoint: `sprezzature_maps.api:app` has no `/mcp`, which is mounted
# only when `sprezzature_maps.mcp` is imported. Override the command for MCP
# or for the command line:
#
#   docker run --rm -p 8000:8000 IMAGE sprezzature-maps-mcp --host 0.0.0.0
#   docker run --rm -v "$PWD:/out" IMAGE make-map choropleth --out /out/world.svg
CMD ["uvicorn", "sprezzature_maps.api:app", "--host", "0.0.0.0", "--port", "8000"]
