#!/usr/bin/env python
"""Discover Composio tools for transcribing audio/video."""
import json
import sys

from composio import Composio


def main():
    composio = Composio()
    query = "transcribe audio video to text"
    try:
        results = composio.search_tools(query=query)
    except AttributeError:
        results = composio.tools.search(query=query)
    print(json.dumps(results, indent=2)[:6000])


if __name__ == "__main__":
    main()
