#! /usr/bin/env python3
"""
This module harmonizes the different steps necessary to create a CLM input data
tarball used within the NorESM land sites platform setup. It extracts data from
both global and regional datasets. Currently, it only supports single-site
simulations. Broadly, it is a wrapper for executing tools from the CTSM and
CIME libraries.

To run this script on SAGA:

git clone https://github.com/NordicESMhub/ctsm.git
git checkout -b test-fates release-emerald-platform2.0.1

module load Python/3.9.6-GCCcore-11.2.0
module load NCL/6.6.2-intel-2019b
module load netCDF-Fortran/4.5.2-iimpi-2019b

There are two ways to execute this script:
./create_forcing_classic.py -f instruction.yaml
=> For using a single yaml recipe file (see documentation)

./create_forcing_classic.py -d path/to/yaml/collection
=> For using a number of yaml recipies contained in a common directory

Parts of the code are heavily inspired by NCARs subset_data.py tool:
https://github.com/ESCOMP/CTSM/blob/master/tools/site_and_regional/subset_data.py
"""

### Library imports
# Python standard library
import sys
import logging
import logging.handlers
import subprocess
import argparse
import glob
import yaml

from datetime import date
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
from pathlib import Path
from typing import Union

################################################################################
"""
Define argument parser
"""
################################################################################
def get_parser():
        """Get parser object for this script."""

        parser = ArgumentParser(description=__doc__,
        formatter_class=RawTextHelpFormatter)

        parser.add_argument("-f", "--file",
        help="path to a single yaml file containing the input data extraction "\
        + "recipe.", action="store", dest="yaml_file", required=False,
        type = str, default='')

        parser.add_argument("-d", "--dir",
        help="path to a directory containing yaml files with input data "\
        + "extraction recipes.", action="store", dest="yaml_dir", required=False,
        default='')

        return parser

################################################################################
"""
Define logger
"""
################################################################################
class StreamToLogger(object):
    """
    Custom class to log all stdout and stderr streams.
    modified from:
    https://www.electricmonk.nl/log/2011/08/14/redirect-stdout-and-stderr-to-a-logger-in-python/
    """
    def __init__(self, stream, logger, log_level=logging.INFO,
                 also_log_to_stream=False):
        self.logger = logger
        self.stream = stream
        self.log_level = log_level
        self.linebuf = ''
        self.also_log_to_stream = also_log_to_stream

    @classmethod
    def setup_stdout(cls, also_log_to_stream=True):
        """
        Setup logger for stdout
        """
        stdout_logger = logging.getLogger('STDOUT')
        sl = StreamToLogger(sys.stdout, stdout_logger, logging.INFO,
        also_log_to_stream)
        sys.stdout = sl

    @classmethod
    def setup_stderr(cls, also_log_to_stream=True):
        """
        Setup logger for stdout
        """
        stderr_logger = logging.getLogger('STDERR')
        sl = StreamToLogger(sys.stderr, stderr_logger, logging.ERROR,
        also_log_to_stream)
        sys.stderr = sl

    def write(self, buf):
        temp_linebuf = self.linebuf + buf
        self.linebuf = ''
        for line in temp_linebuf.splitlines(True):
            if line[-1] == '\n':
                self.logger.log(self.log_level, line.rstrip())
            else:
                self.linebuf += line

    def flush(self):
        if self.linebuf != '':
            self.logger.log(self.log_level, self.linebuf.rstrip())
        self.linebuf = ''

################################################################################

def setup_logging(log_file, log_level):
    """
    Setup logging to log to console and log file.
    """

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # setup log file
    one_mb = 1000000
    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=one_mb,
    backupCount=10)

    fmt = logging.Formatter(
            '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
            datefmt='%y-%m-%d %H:%M:%S')

    handler.setFormatter(fmt)
    root_logger.addHandler(handler)

    # setup logging to console
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    root_logger.addHandler(stream_handler)

    # redirect stdout/err to log file
    StreamToLogger.setup_stdout()
    StreamToLogger.setup_stderr()

################################################################################
"""
Helper functions
"""
################################################################################
def read_yaml_as_dict(file_path: Union[Path, str]) -> dict:
    """Opens a yaml file and returns the content as a dict type."""

    if isinstance(file_path, str):
        file_path = Path(file_path)

    if file_path.suffix != '.yml' and file_path.suffix != '.yaml':
        raise ValueError(f"'{file_path}' is not a yaml file!")

    with open(file_path, 'r') as stream:
        dict_ = yaml.safe_load(stream)

    return dict_

################################################################################
"""
Classes
"""
################################################################################
class SinglePointExtractor:

    minimum_required = ('urban', 'clm', 'fates', 'snicar_drt', 'snicar_optics',
    'fire', 'GSWP3', 'topology', 'NASA_LIS', 'top_mozart_aero')

    def __init__(self, instruction_dict: dict):
        self.instruction_dict = instruction_dict
        self.version = self.instruction_dict['version']
        self.site_code = self.instruction_dict['site_code']
        self.date = date.today().strftime("%Y-%m-%d")

        self.output_dir = \
        Path(self.instruction_dict['output_dir']) / f"{self.site_code}_{self.version}"
        if not self.output_dir.is_dir():
            self.make_dir(self.output_dir)

        self.ctsm_path = Path(self.instruction_dict['ctsm_path'])
        self.root_path = Path(self.instruction_dict['nc_input_paths']['root_path'])

        self.site_name = self.instruction_dict['site_name']
        self.site_code = self.instruction_dict['site_code']
        self.lat = self.instruction_dict['coordinates']['lat']
        self.lon = self.instruction_dict['coordinates']['lon']

        if not self.ceck_minimum_required(instruction_dict):
            sys.exit()

    @staticmethod
    def make_dir(path: Union[Path, str]) -> bool:
        if isinstance(path, str):
            path = Path(path)
        try:
            path.mkdir(parents=True, exist_ok=False)
            print(f"Created directory '{path}'.")
        except:
            print(f"Error when creating '{path}'. Make sure all parent " \
            + "directories exist and there is no folder with the same name!")
            raise
        return True

    @classmethod
    def print_minimum_required(cls):
        print(f"Please supply at least the following inputs:")
        print(", ".join(val for val in cls.minimum_required))

    def ceck_minimum_required(self, ins_dict: dict) -> bool:
        for key, value in ins_dict.items():
            if isinstance(value, dict):
                self.ceck_minimum_required(value)
            else:
                if value is None and key in self.minimum_required:
                    print(f"Missing: '{key}'!")
                    self.print_minimum_required()
                    return False
        return True

    ############################################################################
    def create_land_forcing(self):
        land_dict = self.instruction_dict['nc_input_paths']['land']
        if land_dict['urban']:
            self._create_urban(land_dict['urban'])
        if land_dict['parameter_files']['clm']:
            self._create_clm_param(land_dict['parameter_files']['clm'])
        if land_dict['parameter_files']['fates']:
            self._create_fates_param(land_dict['parameter_files']['fates'])

    def create_atm_forcing(self):
        pass

    def create_share_forcing(self):
        share_dict = self.instruction_dict['nc_input_paths']['share']
        if share_dict['script']:
            print(f"Creating script file...")
            self._create_script()

    ############################################################################
    'Land forcing'
    ############################################################################
    def _create_script(self):
        ### Create folder
        output_path = self.output_dir / 'share' / 'scripgrids' / self.site_code
        self.make_dir(output_path)

        ### Call perl script to make script files
        script_path_str = \
        str(self.ctsm_path / 'ctsm/tools/mkmapdata/mknoocnmap.pl')

        cmd = script_path_str \
        + f" -centerpoint {self.lat},{self.lon} -name {self.site_code} " \
        + "-dx 0.01 -dy 0.01;"
        subprocess.run(cmd, shell=True, check=True)

        ### Move new files to created script directory
        cmd = f"mv {script_path_str}/tools/mkmapgrids/*{self.site_code}*.nc " \
        + f"{output_path}"
        subprocess.run(cmd, shell=True, check=True)

        return True

    def _create_domain(self):
        """TODO: Fix whatever this is:"""
        #### Compile (Only need to be run at the first time, better to run separately)
        #cd src/
        #../../../configure --macros-format Makefile --mpilib mpi-serial --machine saga
        #. ./.env_mach_specific.sh ; gmake

        # Create folder
        output_path = self.output_dir / 'share' / 'domains' / self.site_code
        self.make_dir(output_path)

        ### Call scripts to make domain files
        domain_scripts_path_str = \
        str(self.ctsm_path / '/cime/tools/mapping/gen_domain_files/')

        cmd = domain_scripts_path_str + f"/src/.env_mach_specific.sh;" \
        + domain_scripts_path_str + f"/gen_domain -m "\
        + f"{self.output_dir}/share/scripgrids/{self.site_code}/"\
        + f"map_{self.site_code}_noocean_to_{self.site_code}_nomask" \
        + f"_aave_da_{self.date}.nc -o ${self.site_code} -l ${self.site_code}"

        subprocess.run(cmd, shell=True, check=True)

        ### Move new files to created script directory
        cmd = f"mv {domain_scripts_path_str}/domain.lnd.{self.site_code}_{self.site_code}.{self.date}.nc " \
        + f"domain.lnd.{self.site_code}.{self.date}.nc;" \
        + f"mv {domain_scripts_path_str}/domain*{self.site_code}*.nc " \
        + f"{output_path};"
        subprocess.run(cmd, shell=True, check=True)

        return True

    def _create_mapping(self):
        """TODO: Fix whatever this is:"""
        ##### Modify regridbatch.sh. This has been done in "fates_emerald_api".

        # Create folder
        output_path = self.output_dir / 'lnd' / 'clm2' / 'mappingdata' / \
        'maps' / self.site_code
        self.make_dir(output_path)

        ### Call scripts to make mapping files
        map_scripts_path_string = str(self.ctsm_path / '/tools/mkmapdata')

        cmd = f"{map_scripts_path_string}/regridbatch.sh 1x1_{self.site_code} "\
        + f"{self.output_dir}/share/scripgrids/{self.output_dir}/SCRIPgrid_{self.output_dir}_nomask_c{self.date}.nc;" \
        + f"mv {map_scripts_path_string}/map*{self.output_dir}*.nc " \
        + f"{output_path};"
        subprocess.run(cmd, shell=True, check=True)

        return True

    def _create_surface(self):
        """TODO: Fix whatever this is"""
        #### Compile (Only need to be run at the first time, better to run separately)
        #module load netCDF-Fortran/4.5.2-iimpi-2019b
        #Modify Makefile.common. This has been done in "fates_emerald_api".
        #gmake clean
        #gmake

        # Create folder
        output_path = self.output_dir/'lnd'/'clm2'/'surfdata_map'/self.site_code
        self.make_dir(output_path)

        ### Call scripts to make mapping files
        surface_scripts_path_string = str(self.ctsm_path / '/tools/mksurfdata_map')
        cmd = f'''{surface_scripts_path_string}/mksurfdata.pl -no-crop -res usrspec -usr_gname 1x1_{self.site_code} -usr_gdate {self.date} -usr_mapdir {self.output_dir}/lnd/clm2/mappingdata/maps/{self.site_code} -dinlc {self.root_path} -hirespft -years "2005" -allownofile;'''
        + f'''mv surfdata*{self.site_code}* {output_path}'''
        subprocess.run(cmd, shell=True, check=True)

        return True

    def _create_aerosol_deposition(self):
        """TODO: Fix whatever this is"""
        #### You need to modify the settings in "aerdep_site_clm5.ncl" before doing the following command. See detailed instructions in the file.

        # Create folder
        output_path = self.output_dir / \
        'lnd' / 'clm2' / 'mappingdata' / 'maps' / self.site_code
        self.make_dir(output_path)

        ### Call scripts to make mapping files
        aero_scripts_path_string = \
        str(self.ctsm_path / '/tools/emerald_sites_tools')

        cmd = f"{aero_scripts_path_string}/ncl aerdep_site_clm5.ncl"
        subprocess.run(cmd, shell=True, check=True)

        return True


    def _create_topography(self):
        """Fix whatever this is:"""
        #### You need to modify the settings in "urbandata_site_clm5.ncl" before doing the following command. See detailed instructions in the file.

        # Create folder
        output_path = self.output_dir / \
        'lnd' / 'clm2' / 'mappingdata' / 'maps' / self.site_code
        self.make_dir(output_path)

        ### Call scripts to make mapping files
        aero_scripts_path_string = \
        str(self.ctsm_path / '/tools/emerald_sites_tools')

        cmd = f"{aero_scripts_path_string}/ncl aerdep_site_clm5.ncl"
        subprocess.run(cmd, shell=True, check=True)

        return True

    def _create_urban(self, file_path: Union[str, Path]):
        pass
    def _create_clm_param(self, file_path: Union[str, Path]):
        pass
    def _create_fates_param(self, file_path: Union[str, Path]):
        pass

    ############################################################################
    'Atmospheric forcing'
    ############################################################################


################################################################################
"""
Main function
"""
################################################################################
def main():
    args = get_parser().parse_args()

    today = date.today()
    today_string = today.strftime("%Y-%m-%d")

    work_dir = Path(__file__).parent
    log_file = work_dir / f'{today_string}.log'
    log_level =  logging.DEBUG
    setup_logging(log_file, log_level)
    log = logging.getLogger(__name__)

    recipe_dict_list = []

    if(args.yaml_dir):
        yaml_path = Path(args.yaml_dir)

        if not yaml_path.is_dir():
            print(f"Provided path '{yaml_dir}' does not exist!")
            sys.exit()

        # Grab all files ending with .yaml or .yml
        yaml_files = \
        glob.glob(str(yaml_path)+"/*.yml") + glob.glob(str(yaml_path)+"/*.yaml")

        for file in yaml_files:
            recipe_dict_list.append(read_yaml_as_dict(file))

        if not recipe_dict_list:
            print(f"No yaml files found in '{yaml_dir}'!")
            sys.exit()

    elif(args.yaml_file):
        yaml_file_path = Path(args.yaml_file)

        if not yaml_file_path.is_file():
            print(f"The yaml file '{args.yaml_file}' does not exist!")
        recipe_dict_list.append(read_yaml_as_dict(yaml_file_path))

    else:
        print("You need to provide at least one argument. Run "\
        + "'python3 create_forcing_classic.py --help' for details.")
        sys.exit()

    ###################### START CREATING INPUT DATA ###########################
    for site_dict in recipe_dict_list:

        extractor = SinglePointExtractor(site_dict)

        extractor.create_land_forcing()
        extractor.create_share_forcing()


if __name__ == "__main__":
    main()
