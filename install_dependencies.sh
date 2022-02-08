#! /usr/bin/bash
set -e

# Repo links and release version
CTSM_REMOTE=https://github.com/lasseke/ctsm.git
CTSM_RELEASE_TAG=release-emerald-platform3.0.0
DOT_CIME_REMOTE=https://github.com/MetOs-UiO/dotcime.git

# Set paths
DIR_CTSM=$HOME/ctsm
DIR_CODE=$PWD/$(dirname "${BASH_SOURCE[0]}")
DIR_ENV=$DIR_CODE/env

DIR_INST=$DIR_CODE/install
DIR_CONF=$DIR_CODE/config

# Get CTSM (if needed)
if ! [ -d $DIR_CTSM ]; then
    module load git/2.23.0-GCCcore-8.3.0
    git clone $CTSM_REMOTE $DIR_CTSM
    cd $DIR_CTSM
    git checkout tags/$CTSM_RELEASE_TAG -b nlp-input-temp
    python3 ./manage_externals/checkout_externals
    module purge
else
    echo "WARNING! A clone of CTSM already exists in $HOME/ctsm."
    echo "If you run into errors, try to (re-)move it and re-run the"
    echo "installation."
fi;

# CIME porting (if needed)
if ! [ -d $HOME/.cime ]; then
    module load git/2.23.0-GCCcore-8.3.0
    git clone $DOT_CIME_REMOTE $HOME/.cime
    module purge
else
    echo "WARNING! The hidden .cime/ folder already exists in $HOME."
    echo "If you run into errors, try to (re-)move it and re-run the"
    echo "installation."
fi;

# Compile gen_domain (if needed)
cd $DIR_CTSM/cime/tools/mapping/gen_domain_files
if ! [ -f gen_domain ]; then
    cd src
    ../../../configure --macros-format Makefile --mpilib mpi-serial --machine saga
    . ./.env_mach_specific.sh ; gmake
fi;
cd $DIR_CODE

# Compile mksurfdat (if needed)
cd $DIR_CTSM/tools/mksurfdata_map
if ! [ -f mksurfdata_map ]; then
    cd src
    cp $DIR_CONF/Makefile.common ./Makefile.common
    module load netCDF-Fortran/4.5.2-iimpi-2019b
    gmake clean
    gmake -j 8
    module purge
fi;
cd $DIR_CODE

# Create virtual environment
module load Python/3.9.6-GCCcore-11.2.0
if [ -d $DIR_ENV ]; then
    rm -rf $DIR_ENV
fi
python3 -m venv $DIR_ENV
source $DIR_ENV/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r $DIR_CODE/requirements.txt
deactivate
module purge
