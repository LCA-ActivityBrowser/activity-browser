#!/bin/bash

# Initialize Conda in the shell session
eval "$(conda shell.bash hook)"

# Check if the 'ab' environment exists
if ! conda env list | grep -q "\bab\b"; then
    # Create a Conda environment named 'ab' with 'activity-browser' package from conda-forge
    conda create -y -n ab -c conda-forge activity-browser
fi

