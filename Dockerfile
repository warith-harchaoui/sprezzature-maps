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

# Serve the thing the image was built with: the HTTP API, the gallery page at
# `/`, and the MCP endpoint at `/mcp`, all on port 8000. `sprezzature-maps-mcp`
# mounts `/mcp` on the same FastAPI app that carries the `/v1/...` routes, so
# one process and one port answer both. Until 2026-11-04 the default ran
# `uvicorn sprezzature_maps.api:app`, which has no `/mcp`, and an agent pointed
# at the container found nothing to call. Override the command for the
# command line:
#
#   docker run --rm -v "$PWD:/out" IMAGE make-map choropleth --out /out/world.svg
CMD ["sprezzature-maps-mcp", "--host", "0.0.0.0", "--port", "8000"]
