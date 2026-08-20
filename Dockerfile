FROM python:3.12-slim

WORKDIR /app

# Neither sprezzature-maps nor sprezzature-figures is on PyPI yet (see
# README.md § Install); pull the sibling dependency the same way the CI
# workflow and the local dev setup both do.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 https://github.com/warith-harchaoui/sprezzature-figures /sprezzature-figures \
    && pip install --no-cache-dir -e /sprezzature-figures

COPY . .

RUN pip install --no-cache-dir -e ".[cli,api,mcp]"

CMD ["python", "scripts/make_choropleth.py", "--help"]
