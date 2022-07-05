#! /usr/bin/env python3
"""
This module harmonizes the different steps necessary to create a CLM input data
tarball used within the NorESM land sites platform setup. It extracts single-point 
forcing data from global and regional datasets. Broadly, it is a wrapper for 
executing tools from the CTSM and CIME libraries.

To run this script on SAGA run the following commands:

# WARNING! Move existing copies of .cime and ctsm from your home directory (~) to be
# on the safe side.

# First time installation
cd nlp-input-handling/install
chmod +x ./install_dependencies.sh
./install_dependencies.sh

# Load dependencies, necessary each time you log in again
cd ~/nlp-input-handling
. ./load_dependencies.sh

There are two ways to execute this script:
./create_forcing_classic.py -f [instruction_file_name].yaml
=> For using a single yaml recipe file (see documentation)

./create_forcing_classic.py -d path/to/yaml/collection
=> For using a number of yaml recipies contained in a common directory

Parts of the code are heavily inspired by NCARs subset_data.py tool:
https://github.com/ESCOMP/CTSM/blob/master/tools/site_and_regional/subset_data.py
"""

# Library imports
# Python standard library
import sys
import logging
import logging.handlers
import subprocess
import glob
import yaml

from datetime import date
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
from pathlib import Path
from typing import Union

###############################################################################
"""
Define argument parser
"""
###############################################################################


def get_parser():
    """Get parser object for this script."""

    parser = ArgumentParser(description=__doc__,
                            formatter_class=RawTextHelpFormatter)

    parser.add_argument("-f", "--file",
                        help="path to a single yaml file containing the input "
                        + "data extraction recipe.", action="store",
                        dest="yaml_file", required=False, type=str,
                        default='site_instructions_template.yaml')

    parser.add_argument("-d", "--dir",
                        help="path to a directory containing yaml files with "
                        + "input data extraction recipes.", action="store",
                        dest="yaml_dir", required=False, default='')

    parser.add_argument("-m", "--machine",
                        help="name of one of the machines defined in "
                        + "'machine_properties.yaml'", action="store",
                        dest="machine", required=False, default='saga')
    return parser


###############################################################################
"""
Define logger
"""
###############################################################################


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

###############################################################################


def setup_logging(log_file, log_level):
    """
    Setup logging to log to console and log file.
    """

    logging.raiseExceptions = True
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


###############################################################################
"""
Helper functions
"""
###############################################################################


def read_yaml_as_dict(file_path: Union[Path, str]) -> dict:
    """Opens a yaml file and returns the content as a dict type."""

    if isinstance(file_path, str):
        file_path = Path(file_path)

    if file_path.suffix != '.yml' and file_path.suffix != '.yaml':
        raise ValueError(f"'{file_path}' is not a yaml file!")

    with open(file_path, 'r') as stream:
        dict_ = yaml.safe_load(stream)

    return dict_


###############################################################################
"""
Classes
"""
###############################################################################


class Machine:

    # Path to the machine definition yaml file, keep in same folder!
    definition_yaml_file = Path(__file__).parent / 'machine_properties.yaml'

    def __init__(self, name: str):
        self.name = name
        self.property_dict = self._read_properties(machine_name=self.name)

    def _read_properties(self, machine_name):
        dict_ = read_yaml_as_dict(file_path=self.definition_yaml_file)
        return(dict_['machines'][machine_name])

    def generate_load_module_str(self, module_type: str):
        return "module load " \
            + f"{self.property_dict['module_names'][module_type]};"

    @classmethod
    def get_purge_str(cls):
        return "module purge;"

    def get_name(self):
        return self.name

    def __str__(self):
        return f"Machine name: {self.name}"

###############################################################################
###############################################################################


class SinglePointExtractor:
    """Documentation!"""

    minimum_required = ('surface', 'urban', 'aging_parameters',
                        'optical_properties', 'fire', 'clm', 'fates',
                        'topography', 'lightning', 'aerosol_deposition',
                        'root_path')

    scrip_map_file_path = None
    scrip_grid_file_path = None
    domain_file_path = None

    def __init__(self, instruction_dict: dict, machine: Machine):

        self.instruction_dict = instruction_dict
        self.machine = machine

        self.version = self.instruction_dict['version']
        self.date = date.today().strftime("%Y-%m-%d")
        self.ctsm_date = date.today().strftime("%y%m%d")

        self.site_code = self.instruction_dict['site_code']
        self.lat = self.instruction_dict['coordinates']['lat']
        self.lon = self.instruction_dict['coordinates']['lon']
        self.elevation = self.instruction_dict['elevation']

        # Instantiate empty list to store created file paths
        self.created_files_path_list = []

        # Repo dir
        self.code_dir = Path(__file__).expanduser().absolute().parent
        self.ncl_script_dir = self.code_dir / 'external_scripts' / 'ncl'

        # LOCAL OUTPUT DIR
        self.output_dir = \
            (Path(self.instruction_dict['output']['local_output'])
             / f"{self.site_code}_{self.version}").expanduser()
        if not self.output_dir.is_dir():
            self.make_dir(self.output_dir)
        else:
            input_bool = True
            while(input_bool):
                user_input_rmdir = \
                    input(f"Warning: {self.output_dir} already exists. "
                        + "Enter 'a' to abort or 'd' to delete the existing folder: ")
                if user_input_rmdir.lower() == "a":
                    input_bool = False
                    sys.exit()
                elif user_input_rmdir.lower() == "d":
                    self.run_process(f"rm -rf {self.output_dir};")
                    self.make_dir(self.output_dir)
                    input_bool = False
                else:
                    pass

        # TAR DIR
        self.tar_output_dir = \
            (Path(self.instruction_dict['output']['tar_output_dir'])
             / f"{self.site_code}_{self.version}").expanduser()
        if not self.tar_output_dir.is_dir():
            self.make_dir(self.tar_output_dir)
        else:
            input_bool = True
            while(input_bool):
                user_input_rmdir = \
                    input(f"Warning: {self.tar_output_dir} already exists. "
                        + "Enter 'a' to abort or 'd' to delete the existing folder: ")
                if user_input_rmdir.lower() == "a":
                    input_bool = False
                    sys.exit()
                elif user_input_rmdir.lower() == "d":
                    self.run_process(f"rm -rf {self.tar_output_dir};")
                    self.make_dir(self.tar_output_dir)
                    input_bool = False
                else:
                    pass

        # CTSM dir for mapping files
        self.ctsm_path = Path(self.instruction_dict['ctsm_path']).expanduser()
        self.root_path = \
            Path(self.instruction_dict['nc_input_paths']
                 ['root_path']).expanduser()

        # Run some input checks
        if not self.ceck_minimum_required(instruction_dict):
            sys.exit()
        self._check_shared_input()

    ###########################################################################
    ###########################################################################
    ###########################################################################

    @staticmethod
    def make_dir(path: Union[Path, str]) -> bool:
        if isinstance(path, str):
            path = Path(path)
        try:
            path.mkdir(parents=True, exist_ok=False)
            print(f"Created directory '{path}'.")
        except:
            print(f"Error when creating '{path}'. Make sure it is valid and "
                  + "that there is no existing folder with the same name!")
            raise
        return True

    ###########################################################################

    @classmethod
    def print_minimum_required(cls):
        print("Please supply at least the following inputs:")
        print(", ".join(val for val in cls.minimum_required))

    ###########################################################################

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

    def _check_shared_input(self) -> bool:
        """Check the user input for shared components, raises ValueError"""

        dict_ = self.instruction_dict['nc_input_paths']['share']
        for key, val in dict_.items():
            if not val['create_new']:
                if val['path'] is None:
                    raise ValueError(
                        "You must provide a path if 'create_new' is 'no'!")

        if not dict_['SCRIP']['create_new']:
            self.scrip_map_file_path = \
                Path(dict_['SCRIP']['map_path']).expanduser()
            self.scrip_grid_file_path = \
                Path(dict_['SCRIP']['grid_path']).expanduser()
        if not dict_['domain']['create_new']:
            self.domain_file_path = \
                Path(dict_['domain']['path']).expanduser()

        return True

    ###########################################################################

    @staticmethod
    def run_process(cmd, env=None):
        """Run a command via subprocess.run()"""

        print(f'\nEXECUTING\n{cmd}\n')
        proc = subprocess.run(cmd, env=env, shell=True, check=True,
                              capture_output=True)
        print((proc.stderr).decode("utf-8"))
        print((proc.stdout).decode("utf-8"))
        print('DONE!\n')

        return str(proc.stdout)

    ###########################################################################

    @staticmethod
    def get_run_ncl_string(ncl_file_path: str, **kwargs) -> str:
        """
        Generate a string for running ncl files with arbitrary nr. of arguments
        """

        cmd = "ncl "
        cmd += " ".join([f"""'{key}="{val}"'""" if isinstance(val, str)
                         else f"{key}={val}" for key, val in kwargs.items()])
        cmd += f" {ncl_file_path};"

        return cmd

    ###########################################################################

    def _add_file_path_to_list(self, path: Path):
        self.created_files_path_list.append(path)

    ###########################################################################
    ###########################################################################
    ###########################################################################

    def create_share_forcing(self):
        """Run functions to create shared forcing files"""

        print("Start creating shared forcing...")
        share_dict = self.instruction_dict['nc_input_paths']['share']
        if share_dict['SCRIP']['create_new']:
            print("Creating new SCRIP file...")
            self._create_scrip()
            self._create_mapping()
        if share_dict['domain']['create_new']:
            print("Creating new domain file...")
            self._create_domain()

    ###########################################################################

    def create_land_forcing(self):
        """Run functions to create land forcing files"""

        print("Start creating land forcing...")

        self._create_surface()
        self._create_urban()
        self._add_snow_files()
        self._create_fire()
        self._add_parameter_files()

    ###########################################################################

    def create_atm_forcing(self):
        """Run functions to create atmospheric forcing files"""

        print("Start creating atmospheric forcing...")

        self._create_climate()
        self._create_topography()
        self._create_atm_lightning()
        self._create_atm_aerosol()

    ###########################################################################
    ###########################################################################
    '''Share forcing functions'''
    ###########################################################################
    ###########################################################################

    def _create_scrip(self):
        """Create a new no-ocean SCRIP file using ctsm's mknoocnmap.pl"""

        output_path = self.output_dir / 'share' / 'scripgrids' / self.site_code
        self.make_dir(output_path)

        # Call perl script to make script files
        script_path_str = \
            str(self.ctsm_path / 'tools' / 'mkmapdata' / 'mknoocnmap.pl')

        # Execute script with site arguments
        # LOAD NCL
        cmd = self.machine.get_purge_str()
        cmd += self.machine.generate_load_module_str('ncl')
        cmd += script_path_str \
            + f" -centerpoint {self.lat},{self.lon} -name {self.site_code} " \
            + "-dx 0.01 -dy 0.01;"
        # Copy output file
        cmd += f"mv {self.code_dir}/*{self.site_code}*.nc "\
            + f"{output_path}/;"  # Trailing "/" important!
        cmd += self.machine.get_purge_str()

        # RUN
        self.run_process(cmd)

        # Retrieve file names for created SCRIP grids
        nc_file_list = glob.glob(str(output_path) + f"/*{self.site_code}*.nc")
        # Add to created files list
        _ = [self._add_file_path_to_list(Path(f)) for f in nc_file_list]

        # Update SCRIP map variables
        file_expr = f"/map_{self.site_code}_noocean_to_{self.site_code}" \
            + f"_nomask_aave_da_{self.ctsm_date}.nc"
        scrip_file = glob.glob(str(output_path) + file_expr)

        if len(scrip_file) == 1:
            self.scrip_map_file_path = Path(scrip_file[0])
        else:
            raise ValueError(f"More than one or no file matching '{file_expr}'"
                             + f" in {output_path}!")

        # Update SCRIP grid variable
        file_expr = f"/SCRIPgrid_{self.site_code}_nomask_c{self.ctsm_date}.nc"
        scrip_file = glob.glob(str(output_path) + file_expr)

        if len(scrip_file) == 1:
            self.scrip_grid_file_path = Path(scrip_file[0])
        else:
            raise ValueError(f"More than one or no file matching '{file_expr}'"
                             + f" in {output_path}!")

        return True

    ###########################################################################

    def _create_domain(self):
        """Create domain file using ctsm's ./gen_domain"""

        # Create folder
        output_path = self.output_dir / 'share' / 'domains' / self.site_code
        self.make_dir(output_path)
        # Create domain file script
        script_path_str = str(self.ctsm_path / 'cime' / 'tools'
                              / 'mapping' / 'gen_domain_files')
        script_name = "gen_domain"

        cmd = self.machine.get_purge_str()
        cmd += f". {script_path_str}/src/.env_mach_specific.sh;"
        cmd += f"{script_path_str}/{script_name} -m {self.scrip_map_file_path} " \
            + f"-o {self.site_code} -l {self.site_code};"
        cmd += self.machine.get_purge_str()

        # RUN
        self.run_process(cmd)

        # Move new files to created script directory
        cmd = f"mv domain.lnd.{self.site_code}_{self.site_code}" \
            + f".{self.ctsm_date}.nc " \
            + f"domain.lnd.{self.site_code}.{self.ctsm_date}.nc;" \
            + f"mv domain*{self.site_code}*.nc " \
            + f"{output_path}/;"
        # RUN
        self.run_process(cmd)

        # Set variable
        self.domain_file_path = output_path / \
            f"domain.lnd.{self.site_code}.{self.ctsm_date}.nc"

        # Add to created files list
        domain_file_list = \
            glob.glob(str(output_path) + f"/*{self.site_code}*.nc")
        _ = [self._add_file_path_to_list(Path(f)) for f in domain_file_list]

        return True

    ###########################################################################

    def _create_mapping(self):
        """Create a new mapping file using ctsm's regridbatch.sh"""

        # Create folder
        output_path = self.output_dir / 'lnd' / 'clm2' / 'mappingdata' / \
            'maps' / self.site_code
        self.make_dir(output_path)

        # Call scripts to make mapping files
        script_path_string = str(self.ctsm_path / 'tools' / 'mkmapdata')
        script_name = "regridbatch_nlp.sh"

        cmd = self.machine.get_purge_str()
        cmd += f"cd {script_path_string};" \
            + f"{script_path_string}/{script_name} 1x1_{self.site_code} " \
            + f"{self.scrip_grid_file_path};" \
            + f"mv map*{self.site_code}*.nc {output_path}/;"
        cmd += self.machine.get_purge_str()
        cmd += f"cd {self.code_dir};"

        # RUN
        self.run_process(cmd)

        # Add to created files list
        mapping_file_list = \
            glob.glob(str(output_path) + f"/map*{self.site_code}*.nc")
        _ = [self._add_file_path_to_list(Path(f)) for f in mapping_file_list]

        return True

    ###########################################################################
    ###########################################################################

    def _create_surface(self):
        """Create surface map from previously created mapping files"""

        # Create folder
        output_path = self.output_dir / 'lnd' / 'clm2' / 'surfdata_map' \
            / self.site_code
        self.make_dir(output_path)

        # Call scripts to make mapping files
        script_path_string = str(self.ctsm_path / 'tools' / 'mksurfdata_map')
        script_name = "mksurfdata.pl"

        # Define map dir
        map_dir_path = self.output_dir / 'lnd' / 'clm2' / 'mappingdata' / \
            'maps' / self.site_code

        cmd = self.machine.get_purge_str()
        cmd += self.machine.generate_load_module_str('ncl')
        cmd += "ulimit -s unlimited;"

        # TODO: What does this script do exactly?
        # What is "years"? Does this need to be adjustable? (also simyr2005)

        cmd += f"cd {script_path_string};" \
            + f"./{script_name} -no-crop -res usrspec -usr_gname " \
            + f"1x1_{self.site_code} -usr_gdate {self.ctsm_date} -usr_mapdir" \
            + f" {map_dir_path} -dinlc {self.root_path} -hirespft " \
            + '''-years "2005" -allownofile;'''

        cmd += f"mv surfdata_1x1_{self.site_code}_hist_16pfts_Irrig_CMIP6_" \
            + f"simyr2005_c{self.ctsm_date}.nc " \
            + f"surfdata_{self.site_code}_simyr2000.nc;" \
            + f"mv surfdata*{self.site_code}* {output_path}/;"

        cmd += self.machine.get_purge_str()
        cmd += f"cd {self.code_dir};"

        # RUN
        self.run_process(cmd)

        # Add to created files list
        surface_file_list = \
            glob.glob(str(output_path) + f"/surfdata*{self.site_code}*")
        _ = [self._add_file_path_to_list(Path(f)) for f in surface_file_list]

        return True

    ###########################################################################
    ###########################################################################
    '''Land forcing functions'''
    ###########################################################################
    ###########################################################################

    def _add_snow_files(self):
        """Copy SNICAR aerosol .nc files into the land component forcing"""

        # Paths from yaml
        root_str = str(self.root_path)

        out_path = self.output_dir / 'lnd' / 'clm2' / 'snicardata'
        if not out_path.is_dir():
            self.make_dir(out_path)
        out_str = str(out_path)

        snicar_nc_paths = \
            self.instruction_dict['nc_input_paths']['land']['snow']

        cmd = ""
        for nc_in_str in snicar_nc_paths.values():
            if nc_in_str is not None:
                cmd += f"cp {root_str}/{nc_in_str} {out_str}/;"
                # Add to list
                nc_file_name = Path(nc_in_str).name
                self._add_file_path_to_list(
                    Path(out_path / nc_file_name)
                )

        # RUN
        if cmd:
            self.run_process(cmd)

        return True

    ###########################################################################

    def _create_urban(self):
        """Create site .nc file for urban data"""

        # Call script to make urban map
        ncl_script_dir = self.ncl_script_dir
        script_name = "urbandata_site_clm5.ncl"

        # Paths from yaml
        root_str = str(self.root_path)
        nc_in_str = \
            self.instruction_dict['nc_input_paths']['land']['urban']

        out_path = self.output_dir/'lnd'/'clm2'/'urbandata'
        if not out_path.is_dir():
            self.make_dir(out_path)
        out_str = str(out_path)

        # Set up bash cmd
        cmd = self.machine.get_purge_str()
        cmd += self.machine.generate_load_module_str('ncl')

        cmd += self.get_run_ncl_string(
            ncl_file_path=f"{ncl_script_dir}/{script_name}",
            plot_name=str(self.site_code),
            nc_in_file_path=f"{root_str}/{nc_in_str}",
            out_file_path=f"{out_str}/",  # IMPORTANT TO ADD TRAILING "/"!
            domain_file_path=str(self.domain_file_path)
        )
        cmd += self.machine.get_purge_str()

        # RUN
        self.run_process(cmd)

        # Add to list, manually edited to match ncl script behavior
        nc_str_no_suffix = nc_in_str.replace('.nc', '')
        self._add_file_path_to_list(
            Path(out_str+nc_str_no_suffix+"_"+self.site_code+".nc")
        )

        return True

    ###########################################################################

    def _add_parameter_files(self):

        # Paths from yaml
        root_str = str(self.root_path)

        out_path = self.output_dir / 'lnd' / 'clm2' / 'paramdata'
        if not out_path.is_dir():
            self.make_dir(out_path)
        out_str = str(out_path)

        param_dict = \
            self.instruction_dict['nc_input_paths']['land']['parameter_files']

        for nc_in_str in param_dict.values():
            if nc_in_str is not None:
                cmd = f"cp {root_str}/{nc_in_str} {out_str};"
                # RUN
                self.run_process(cmd)

                # Add to list
                nc_file_name = Path(nc_in_str).name
                self._add_file_path_to_list(
                    Path(out_path / nc_file_name)
                )

        return True

    ###########################################################################

    def _create_fire(self):
        """
        Create site/regional fire .nc file, i.e., regridding population density
        """

        # Call scripts to create fire data
        ncl_script_dir = self.ncl_script_dir
        script_name = "popden_site_clm5.ncl"

        # Paths from yaml
        root_str = str(self.root_path)
        nc_in_str = \
            self.instruction_dict['nc_input_paths']['land']['fire']

        out_path = self.output_dir / 'lnd' / 'clm2' / 'firedata'
        if not out_path.is_dir():
            self.make_dir(out_path)
        out_str = str(out_path)

        # Set up bash cmd
        cmd = self.machine.get_purge_str()
        cmd += self.machine.generate_load_module_str('ncl')

        cmd += self.get_run_ncl_string(
            ncl_file_path=f"{ncl_script_dir}/{script_name}",
            plot_name=str(self.site_code),
            nc_in_file_path=f"{root_str}/{nc_in_str}",
            out_file_path=f"{out_str}/",  # IMPORTANT TO ADD TRAILING "/"!
            domain_file_path=str(self.domain_file_path)
        )
        cmd += self.machine.get_purge_str()

        # RUN
        self.run_process(cmd)

        # Add to list, manually edited to match ncl script behavior
        nc_str_no_suffix = nc_in_str.replace('.nc', '')
        self._add_file_path_to_list(
            Path(out_str+nc_str_no_suffix+"_"+self.site_code+".nc")
        )

        return True

    ###########################################################################
    ###########################################################################
    '''Atmospheric forcing'''
    ###########################################################################
    ###########################################################################

    def _create_climate(self):
        """Create climate forcing, currently only using prepared GSWP3 data"""

        # Call scripts to create topography data
        ncl_script_dir = self.ncl_script_dir
        script_name = "prepare_atm_forcing_gswp3.ncl"

        climate_dict = \
            self.instruction_dict['nc_input_paths']['atmosphere']['climate']

        # Paths from yaml
        root_str = str(self.root_path)

        if climate_dict['GSWP3']['root_path']:

            nc_in_str = climate_dict['GSWP3']['root_path']

            out_path = self.output_dir / 'atm' / 'datm7' / 'GSWP3v1' \
                / self.site_code

            if not out_path.is_dir():
                self.make_dir(out_path)
            out_str = str(out_path)

            # Set up bash cmd
            cmd = self.machine.get_purge_str()
            cmd += self.machine.generate_load_module_str('ncl')

            cmd += self.get_run_ncl_string(
                ncl_file_path=f"{ncl_script_dir}/{script_name}",
                plot_name=str(self.site_code),
                nc_in_file_path=f"{root_str}/{nc_in_str}",
                out_file_path=f"{out_str}/",  # IMPORTANT TO ADD TRAILING "/"!
                plot_lat=self.lat,
                plot_lon=self.lon,
                year_start=climate_dict['GSWP3']['year_start'],
                year_end=climate_dict['GSWP3']['year_end']
            )
            cmd += self.machine.get_purge_str()

            # RUN
            self.run_process(cmd)

            # Add dir to list
            self._add_file_path_to_list(out_path)

        return True

    ###########################################################################

    def _create_atm_aerosol(self):
        """Create input .nc file for atmospheric aerosol deposition"""

        # Call scripts to make mapping files
        ncl_script_dir = self.ncl_script_dir
        script_name = "aerdep_site_clm5.ncl"

        # Paths from yaml
        root_str = str(self.root_path)
        nc_in_str = self \
            .instruction_dict['nc_input_paths']['atmosphere']['aerosol_deposition']
        out_path = self.output_dir / 'atm' / 'cam' / 'chem' \
            / 'trop_mozart_aero' / 'aero'
        if not out_path.is_dir():
            self.make_dir(out_path)
        out_str = str(out_path)

        # Set up bash cmd
        cmd = self.machine.get_purge_str()
        cmd += self.machine.generate_load_module_str('ncl')

        cmd += self.get_run_ncl_string(
            ncl_file_path=f"{ncl_script_dir}/{script_name}",
            plot_name=str(self.site_code),
            nc_in_file_path=f"{root_str}/{nc_in_str}",
            out_file_path=f"{out_str}/",  # IMPORTANT TO ADD TRAILING "/"!
            domain_file_path=str(self.domain_file_path)
        )
        cmd += self.machine.get_purge_str()

        # RUN
        self.run_process(cmd)

        # Add to list, manually edited to match ncl script behavior
        nc_str_no_suffix = nc_in_str.replace('.nc', '')
        self._add_file_path_to_list(
            Path(out_str+nc_str_no_suffix+"_"+self.site_code+".nc")
        )

        return True

    ###########################################################################

    def _create_atm_lightning(self):
        """Create input .nc file for lightning"""

        # Call scripts to make lightning files
        ncl_script_dir = self.ncl_script_dir
        script_name = "lightning_site_clm5.ncl"

        # Paths from yaml
        root_str = str(self.root_path)
        nc_in_str = \
            self.instruction_dict['nc_input_paths']['atmosphere']['lightning']

        out_path = self.output_dir/'atm'/'datm7'/'NASA_LIS'
        if not out_path.is_dir():
            self.make_dir(out_path)
        out_str = str(out_path)

        # Set up bash cmd
        cmd = self.machine.get_purge_str()
        cmd += self.machine.generate_load_module_str('ncl')

        cmd += self.get_run_ncl_string(
            ncl_file_path=f"{ncl_script_dir}/{script_name}",
            plot_name=str(self.site_code),
            nc_in_file_path=f"{root_str}/{nc_in_str}",
            out_file_path=f"{out_str}/",  # IMPORTANT TO ADD TRAILING "/"!
            domain_file_path=str(self.domain_file_path)
        )
        cmd += self.machine.get_purge_str()

        # RUN
        self.run_process(cmd)

        # Add to list, manually edited to match ncl script behavior
        nc_str_no_suffix = nc_in_str.replace('.nc', '')
        self._add_file_path_to_list(
            Path(out_str+nc_str_no_suffix+"_"+self.site_code+".nc")
        )

        return True

    ############################################################################

    def _create_topography(self):
        """Create site elevation file to be read by DATM"""

        # Call scripts to create topography data
        ncl_script_dir = self.ncl_script_dir
        script_name = "topo_site_clm5.ncl"

        # Paths from yaml
        root_str = str(self.root_path)
        nc_in_str = \
            self.instruction_dict['nc_input_paths']['atmosphere']['topography']

        out_path = self.output_dir / 'atm' / 'datm7' / 'topo_forcing'
        if not out_path.is_dir():
            self.make_dir(out_path)
        out_str = str(out_path)

        # Set up bash cmd
        cmd = self.machine.get_purge_str()
        cmd += self.machine.generate_load_module_str('ncl')

        cmd += self.get_run_ncl_string(
            ncl_file_path=f"{ncl_script_dir}/{script_name}",
            plot_name=str(self.site_code),
            plot_height=self.elevation,
            nc_in_file_path=f"{root_str}/{nc_in_str}",
            out_file_path=f"{out_str}/",  # IMPORTANT TO ADD TRAILING "/"!
            domain_file_path=str(self.domain_file_path)
        )
        cmd += self.machine.get_purge_str()

        # RUN
        self.run_process(cmd)

        # Add to list, manually edited to match ncl script behavior
        nc_str_no_suffix = nc_in_str.replace('.nc', '')
        self._add_file_path_to_list(
            Path(out_str+nc_str_no_suffix+"_"+self.site_code+".nc")
        )

        return True


###############################################################################

    def tar_output(self):
        """Compress the files in the specified output dir into a Tarball"""

        print("Starting to compress the files...")

        # Add temporary dir to adhere to previous versions
        self.make_dir(self.output_dir / 'inputdata')

        # Tar folder
        tar_dir_name = f"inputdata_version{self.version}_{self.site_code}.tar"

        # Tar output, BUT OMIT LARGE SCRIP AND MAPPING FILES!
        cmd = f"cd {self.output_dir};"
        cmd += "rsync -av --progress . ./inputdata --exclude share/scripgrids "\
            + "--exclude lnd/clm2/mappingdata --exclude inputdata  " \
            + "--exclude *.log --exclude *.namelist --exclude *.ocn.*;"
        cmd += f"tar -cvf {tar_dir_name} inputdata;"
        cmd += f"mv {tar_dir_name} {self.tar_output_dir};"
        cmd += "rm -r inputdata;"

        cmd += f"cd {self.code_dir};"
        self.run_process(cmd)

        return True


###############################################################################
"""End class"""
###############################################################################


###############################################################################
###############################################################################
"""
Main function
"""
###############################################################################
###############################################################################


def main():

    args = get_parser().parse_args()

    today = date.today()
    today_string = today.strftime("%Y-%m-%d")

    work_dir = Path(__file__).parent
    log_file = work_dir / f'{today_string}.log'
    log_level = logging.DEBUG
    setup_logging(log_file, log_level)
    log = logging.getLogger(__name__)

    # Instantiate machine class
    machine = Machine(name=args.machine)

    # Instantiate list that will contain all yaml recipes as dict
    recipe_dict_list = []

    # Directory of files provided via -d?
    if(args.yaml_dir):
        yaml_path = Path(args.yaml_dir)

        if not yaml_path.is_dir():
            print(f"Provided path '{yaml_path}' does not exist!")
            sys.exit()

        # Grab all files ending with .yaml or .yml
        yaml_files = \
            glob.glob(str(yaml_path)+"/*.yml") + \
            glob.glob(str(yaml_path)+"/*.yaml")

        for file in yaml_files:
            recipe_dict_list.append(read_yaml_as_dict(file))

        if not recipe_dict_list:
            print(f"No yaml files found in '{yaml_path}'!")
            sys.exit()

    # Single file provided via -f?
    elif(args.yaml_file):
        yaml_file_path = Path(args.yaml_file)

        if not yaml_file_path.is_file():
            print(f"The yaml file '{args.yaml_file}' does not exist!")
            sys.exit()
        recipe_dict_list.append(read_yaml_as_dict(yaml_file_path))

    # Neither -d nor -f provided?
    else:
        print("You need to provide at least one argument. Run "
              + "'python3 create_forcing_classic.py --help' for details.")
        sys.exit()

    """
    Start creating input data
    """
    for site_dict in recipe_dict_list:

        extractor = SinglePointExtractor(instruction_dict=site_dict,
                                         machine=machine)

        extractor.create_share_forcing()
        extractor.create_land_forcing()
        extractor.create_atm_forcing()

        print("Finished creating inputs. The created files/dirs are:")
        _ = [print(f"- {f}") for f in extractor.created_files_path_list]

        extractor.tar_output()


if __name__ == "__main__":

    main()
