#!/bin/bash
#SBATCH --account=nn2806k
#SBATCH --time=10:00:00
## You can add more args for sbatch here in the same way as above (see "sbatch --help" for all the args), e.g.:
#SBATCH --qos=normal
#SBATCH --job-name=BOR3_input

## Your commands here, e.g.:
module --quiet purge  # Reset the modules to the system default
cd ~/nlp-input-handling
. ./load_dependencies.sh

python3 create_forcing_classic.py -f ./lsp_site_instructions/v1.0.0/site_input_BOR3.yaml