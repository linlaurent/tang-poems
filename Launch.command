#!/bin/bash
cd "$(dirname "$0")"
export DEFAULT_POEM_USER="lin"
uv run streamlit run app.py
