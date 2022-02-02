#! /usr/bin/env python3

"""
This module harmonizes the different steps necessary to create a CLM input data
tarball used within the NorESM land sites platform setup. It extracts data from
both global and regional datasets. Currently, it only supports single-site
simulations.

To run this script on saga:
module load x

To print help to the console:
./create_site_forcing.py --help

"""
