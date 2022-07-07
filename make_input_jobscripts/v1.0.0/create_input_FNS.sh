#!/bin/bash
#SBATCH --account=nn2806k
#SBATCH --time=10:00:00
#SBATCH --job-name=FNS_input
## You can add more args for sbatch here in the same way as above (see "sbatch --help" for all the args), e.g.:
#SBATCH --ntasks=1
#SBATCH --mem-per-cpu=16G
#SBATCH --cpus-per-task=8

## Your commands here, e.g.:
set -o errexit  # Exit the script on any error

module --quiet purge  # Reset the modules to the system default
cd $USERWORK/nlp-input-handling
. ./load_dependencies.sh # Load dependencies for input data creation scripts

python3 create_forcing_classic.py -f ./lsp_site_instructions/v1.0.0/site_input_FNS.yaml