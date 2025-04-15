#!/bin/bash

cd /workspaces/bibliometrics_1/src
pip install --upgrade pip setuptools wheel\
	    && pip install -e ".[dev]"
