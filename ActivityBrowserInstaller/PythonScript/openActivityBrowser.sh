#!/bin/bash

#openActivityBrowser.sh
#Made on 17/05/2024
#Contributed by Thijs Groeneweg and Bryan Owee
#Documented by Arian Farzad
#Last edited on 03/06/2024 by Arian Farzad

#Script for launching the AB that automatically activates the virtual environment
#TODO: Update description

# Initialize Conda in the shell session
eval "$(conda shell.bash hook)"

# Check if the 'ab' environment exists
if ! conda env list | grep -q "\bab\b"; then
    # Create a Conda environment named 'ab' with 'activity-browser' package from conda-forge
    conda create -y -n ab -c conda-forge activity-browser
fi

# Activate the 'ab' environment
conda activate ab

# Run the 'activity-browser' command
activity-browser