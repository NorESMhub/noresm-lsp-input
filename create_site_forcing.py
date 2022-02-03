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

The code is almost entirely based on NCARs subset_data.py tool:
https://github.com/ESCOMP/CTSM/blob/master/tools/site_and_regional/subset_data.py
"""

### Library imports
# Python standard library
import logging
import subprocess
import argparse
from datetime import date
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

# PyPI
import numpy as np
import xarray as xr

################################################################################
"""
Argument parser
"""
################################################################################
def get_parser():
        """Get parser object for this script."""
        parser = ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

        parser.print_usage = parser.print_help

        pt_parser = subparsers.add_parser('point',
                    help = 'Run script for a single point.')


        pt_parser.add_argument('--lat',
                    help='Single point latitude. [default: %(default)s]',
                    action="store",
                    dest="plat",
                    required=False,
                    type = plat_type,
                    default=42.5)
        pt_parser.add_argument('--lon',
                    help='Single point longitude. [default: %(default)s]',
                    action="store",
                    dest="plon",
                    required=False,
                    type = plon_type,
                    default= 287.8 )
        pt_parser.add_argument('--site',
                    help='Site name or tag. [default: %(default)s]',
                    action="store",
                    dest="site_name",
                    required = False,
                    type = str,
                    default = '')
        pt_parser.add_argument('--create_domain',
                    help='Flag for creating CLM domain file at single point. [default: %(default)s]',
                    action="store",
                    dest="create_domain",
                    type = str2bool,
                    nargs = '?',
                    const = True,
                    required = False,
                    default = False)
        pt_parser.add_argument('--create_surface',
                    help='Flag for creating surface data file at single point. [default: %(default)s]',
                    action="store",
                    dest="create_surfdata",
                    type = str2bool,
                    nargs = '?',
                    const = True,
                    required = False,
                    default = True)
        pt_parser.add_argument('--create_landuse',
                    help='Flag for creating landuse data file at single point. [default: %(default)s]',
                    action="store",
                    dest="create_landuse",
                    type = str2bool,
                    nargs = '?',
                    const = True,
                    required = False,
                    default = False)
        pt_parser.add_argument('--create_datm',
                    help='Flag for creating DATM forcing data at single point. [default: %(default)s]',
                    action="store",
                    dest="create_datm",
                    type = str2bool,
                    nargs = '?',
                    const = True,
                    required = False,
                    default = False)
        pt_parser.add_argument('--datm_syr',
                    help='Start year for creating DATM forcing at single point. [default: %(default)s]',
                    action="store",
                    dest="datm_syr",
                    required = False,
                    type = int,
                    default = 1901)
        pt_parser.add_argument('--datm_eyr',
                    help='End year for creating DATM forcing at single point. [default: %(default)s]',
                    action="store",
                    dest="datm_eyr",
                    required = False,
                    type = int,
                    default = 2014)
        pt_parser.add_argument('--datm_from_tower',
                    help='Flag for creating DATM forcing data at single point for a tower data. [default: %(default)s]',
                    action="store",
                    dest="datm_tower",
                    type = str2bool,
                    nargs = '?',
                    const = True,
                    required = False,
                    default = False)
        pt_parser.add_argument('--create_user_mods',
                    help='Flag for creating user mods directory . [default: %(default)s]',
                    action="store",
                    dest="datm_tower",
                    type = str2bool,
                    nargs = '?',
                    const = True,
                    required = False,
                    default = False)
        pt_parser.add_argument('--user_mods_dir',
                    help='Flag for creating user mods directory . [default: %(default)s]',
                    action="store",
                    dest="user_mod_dir",
                    type = str,
                    nargs = '?',
                    const = True,
                    required = False,
                    default = False)
        pt_parser.add_argument('--crop',
                    help='Create datasets using the extensive list of prognostic crop types. [default: %(default)s]',
                    action="store_true",
                    dest="crop_flag",
                    default=False)
        pt_parser.add_argument('--dompft',
                    help='Dominant PFT type . [default: %(default)s] ',
                    action="store",
                    dest="dom_pft",
                    type =int,
                    default=7)
        pt_parser.add_argument('--no-unisnow',
                    help='Turn off the flag for create uniform snowpack. [default: %(default)s]',
                    action="store_false",
                    dest="uni_snow",
                    default=True)
        pt_parser.add_argument('--no-overwrite_single_pft',
                    help='Turn off the flag for making the whole grid 100%% single PFT. [default: %(default)s]',
                    action="store_false",
                    dest="overwrite_single_pft",
                    default=True)
        pt_parser.add_argument('--zero_nonveg',
                    help='Set all non-vegetation landunits to zero. [default: %(default)s]',
                    action="store",
                    dest="zero_nonveg",
                    type =bool,
                    default=True)
        pt_parser.add_argument('--no_saturation_excess',
                    help='Turn off the flag for saturation excess. [default: %(default)s]',
                    action="store",
                    dest="no_saturation_excess",
                    type =bool,
                    default=True)
        pt_parser.add_argument('--outdir',
                    help='Output directory. [default: %(default)s]',
                    action="store",
                    dest="out_dir",
                    type =str,
                    default="/glade/scratch/"+myname+"/single_point/")

        return parser

################################################################################
"""
Helper functions
"""
################################################################################

def str2bool(v):
    """
    Function for converting different forms of
    command line boolean strings to boolean value.
    Args:
        v (str): String bool input
    Raises:
        if the argument is not an acceptable boolean string
        (such as yes or no ; true or false ; y or n ; t or f ; 0 or 1).
        argparse.ArgumentTypeError: The string should be one of the mentioned values.
    Returns:
        bool: Boolean value corresponding to the input.
    """
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected. [true or false] or [y or n]')

################################################################################

def plat_type(x):
    """
    Function to define lat type for the parser
    and
    raise error if latitude is not between -90 and 90.
    """
    x = float(x)
    if (x < -90) or (x > 90):
        raise argparse.ArgumentTypeError("ERROR: Latitude should be between -90 and 90.")
    return x

################################################################################

def plon_type(x):
    """
    Function to define lon type for the parser and
    convert negative longitudes and
    raise error if lon is not between -180 and 360.
    """
    x = float(x)
    if (-180 < x) and (x < 0):
        print ("lon is :", x)
        x= x%360
        print ("after modulo lon is :", x)
    if (x < 0) or (x > 360):
        raise argparse.ArgumentTypeError("ERROR: Latitude of single point should be between 0 and 360 or -180 and 180.")
    return x

################################################################################

def setup_logging(log_file, log_level):
    """
    Setup logging to log to console and log file.
    """

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # setup log file
    one_mb = 1000000
    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=one_mb , backupCount=10)

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
Classes
"""
################################################################################

### Base cases, used for both regional and single-point

class BaseCase:
    """
    Parent class to SinglePointCase and RegionalCase
    ...
    Attributes
    ----------
    create_domain : bool
        flag for creating domain file
    create_surfdata : bool
        flag for creating surface dataset
    create_landuse : bool
        flag for creating landuse file
    create_datm : bool
        flag for creating DATM files
    Methods
    -------
    create_1d_coord(filename, lon_varname , lat_varname,x_dim , y_dim )
        create 1d coordinate variables to enable sel() method
    add_tag_to_filename(filename, tag)
       add a tag and timetag to a filename ending with
       [._]cYYMMDD.nc or [._]YYMMDD.nc
    """
    def __init__(self, create_domain, create_surfdata, create_landuse, create_datm):
        self.create_domain = create_domain
        self.create_surfdata = create_surfdata
        self.create_landuse = create_landuse
        self.create_datm = create_datm

    def __str__(self):
        return  str(self.__class__) + '\n' + '\n'.join((str(item) + ' = ' \
        + str(self.__dict__[item]) for item in sorted(self.__dict__)))

    @staticmethod
    def create_1d_coord(filename, lon_varname , lat_varname , x_dim , y_dim):
        """
        lon_varname : variable name that has 2d lon
        lat_varname : variable name that has 2d lat
        x_dim: dimension name in X -- lon
        y_dim: dimension name in Y -- lat
        """
        print( "Open file: "+filename )
        f1 = xr.open_dataset(filename)

        # create 1d coordinate variables to enable sel() method
        lon0 = np.asarray(f1[lon_varname][0,:])
        lat0 = np.asarray(f1[lat_varname][:,0])
        lon = xr.DataArray(lon0,name='lon',dims=x_dim,coords={x_dim:lon0})
        lat = xr.DataArray(lat0,name='lat',dims=y_dim,coords={y_dim:lat0})

        f2=f1.assign({'lon':lon,'lat':lat})

        f2.reset_coords([lon_varname,lat_varname])
        f1.close()
        return f2

    @staticmethod
    def add_tag_to_filename(filename, tag):
        """
        Add a tag and replace timetag of a filename
        # Expects file to end with [._]cYYMMDD.nc or [._]YYMMDD.nc
        # Add the tag to just before that ending part
        # and change the ending part to the current time tag
        """
        basename = os.path.basename(filename)
        cend = -10
        if ( basename[cend] == "c" ):
           cend = cend - 1
        if ( (basename[cend] != ".") and (basename[cend] != "_") ):
           print ( "Trouble figuring out where to add tag to filename:"+filename )
           os.abort()
        today = date.today()
        today_string = today.strftime("%y%m%d")
        return(basename[:cend]+"_"+tag+"_c"+today_string +'.nc')

    @staticmethod
    def update_metadata(nc):
        # Update attributes
        today = date.today()
        today_string = today.strftime("%Y-%m-%d")

        ## Add current git commit hash
        sha = get_git_sha()

        nc.attrs['Created_on'] = today_string
        nc.attrs['Created_by'] = myname
        nc.attrs['Created_with'] = os.path.abspath(__file__) + " -- "+sha

        # Delete unrelated attributes if they exist
        del_attrs = ['source_code', 'SVN_url', 'hostname', 'history'
                     'History_Log', 'Logname', 'Host', 'Version',
                     'Compiler_Optimized']
        attr_list = nc.attrs

        for attr in del_attrs:
            if attr in attr_list:
                del(nc.attrs[attr])


################################################################################

class SinglePointCase (BaseCase):
    """
    A case to encapsulate single point cases.
    ...
    Attributes
    ----------
    plat : float
        latitude
    plon : float
        longitude
    site_name: str -- default = None
        Site name
    Methods
    -------
    create_tag
        create a tag for single point which is the site name
        or the "lon-lat" format if the site name does not exist.
    create_domain_at_point
        Create domain file at a single point.
    create_landuse_at_point:
        Create landuse file at a single point.
    create_surfdata_at_point:
        Create surface dataset at a single point.
    create_datmdomain_at_point:
        Create DATM domain file at a single point.
    """

    def __init__(self, plat, plon,site_name,
                 create_domain, create_surfdata, create_landuse, create_datm,
                 overwrite_single_pft, dominant_pft, zero_nonveg_landunits,
                 uniform_snowpack, no_saturation_excess):
        super().__init__(create_domain, create_surfdata, create_landuse, create_datm)
        self.plat = plat
        self.plon = plon
        self.site_name = site_name
        self.overwrite_single_pft = overwrite_single_pft
        self.dominant_pft = dominant_pft
        self.zero_nonveg_landunits = zero_nonveg_landunits
        self.uniform_snowpack = uniform_snowpack
        self.no_saturation_excess = no_saturation_excess

    def create_tag(self):
        if self.site_name:
            self.tag = self.site_name
        else:
             self.tag=str(self.plon)+'_'+str(self.plat)

    @staticmethod
    def create_fileout_name( filename,tag):

        basename = os.path.basename(filename)
        items = basename.split('_')
        today = date.today()
        today_string = today.strftime("%y%m%d")
        print (items[-1])
        #new_string = items[0]+"_"+items[2]+"_"+items[3]+"_"+ items[4] \
        #            +"_"+items[5]+"_"+items[6]+"_"+tag+"_c"+today_string+".nc"
        new_string = items[0]+"_"+items[2]+"_"+items[3]+"_"+ items[4] \
                     +"_"+items[5]+"_"+tag+"_c"+today_string+".nc"
        return new_string

    def create_domain_at_point (self):
        print( "----------------------------------------------------------------------")
        print ("Creating domain file at ", self.plon, self.plat)
        # create 1d coordinate variables to enable sel() method
        f2 = self.create_1d_coord(self.fdomain_in, 'xc','yc','ni','nj')
        # extract gridcell closest to plon/plat
        f3 = f2.sel(ni=self.plon,nj=self.plat,method='nearest')
        # expand dimensions
        f3 = f3.expand_dims(['nj','ni'])

        #update attributes
        self.update_metadata(f3)
        f3.attrs['Created_from'] = self.fdomain_in

        wfile=self.fdomain_out
        f3.to_netcdf(path=wfile, mode='w')
        print('Successfully created file (fdomain_out)'+self.fdomain_out)
        f2.close(); f3.close()


    def create_landuse_at_point (self):
        print( "----------------------------------------------------------------------")
        print ("Creating landuse file at ", self.plon, self.plat, ".")
        # create 1d coordinate variables to enable sel() method
        f2 = self.create_1d_coord(self.fluse_in, 'LONGXY','LATIXY','lsmlon','lsmlat')
        # extract gridcell closest to plon/plat
        f3 = f2.sel(lsmlon=self.plon,lsmlat=self.plat,method='nearest')

        # expand dimensions
        f3 = f3.expand_dims(['lsmlat','lsmlon'])
        # specify dimension order
        f3 = f3.transpose(u'time', u'cft', u'natpft', u'lsmlat', u'lsmlon')

        # revert expand dimensions of YEAR
        year = np.squeeze(np.asarray(f3['YEAR']))
        x = xr.DataArray(year, coords={'time':f3['time']}, dims='time', name='YEAR')
        x.attrs['units']='unitless'
        x.attrs['long_name']='Year of PFT data'
        f3['YEAR'] = x

        #update attributes
        self.update_metadata(f3)
        f3.attrs['Created_from'] = self.fluse_in

        wfile = self.fluse_out
        # mode 'w' overwrites file
        f3.to_netcdf(path=wfile, mode='w')
        print('Successfully created file (luse_out)'+self.fluse_out,".")
        f2.close(); f3.close()

    def create_surfdata_at_point(self):
        print( "----------------------------------------------------------------------")
        print ("Creating surface dataset file at ", self.plon, self.plat, ".")
        # create 1d coordinate variables to enable sel() method
        filename = self.fsurf_in
        f2 = self.create_1d_coord(filename, 'LONGXY','LATIXY','lsmlon','lsmlat')
        # extract gridcell closest to plon/plat
        f3 = f2.sel(lsmlon=self.plon,lsmlat=self.plat,method='nearest')
        # expand dimensions
        f3 = f3.expand_dims(['lsmlat','lsmlon']).copy(deep=True)

        # modify surface data properties
        if self.overwrite_single_pft:
            f3['PCT_NAT_PFT'][:,:,:] = 0
            if (self.dominant_pft <16):
                f3['PCT_NAT_PFT'][:,:,self.dominant_pft] = 100
            #else:@@@
        if self.zero_nonveg_landunits:
            f3['PCT_NATVEG'][:,:]  = 100
            f3['PCT_CROP'][:,:]    = 0
            f3['PCT_LAKE'][:,:]    = 0.
            f3['PCT_WETLAND'][:,:] = 0.
            f3['PCT_URBAN'][:,:,]   = 0.
            f3['PCT_GLACIER'][:,:] = 0.
        if self.uniform_snowpack:
            f3['STD_ELEV'][:,:] = 20.
        if self.no_saturation_excess:
            f3['FMAX'][:,:] = 0.

        # specify dimension order
        f3 = f3.transpose(u'time', u'cft', u'lsmpft', u'natpft', u'nglcec', u'nglcecp1', u'nlevsoi', u'nlevurb', u'numrad', u'numurbl', 'lsmlat', 'lsmlon')

        #update lsmlat and lsmlon to match site specific instead of the nearest point
        f3['lsmlon']= np.atleast_1d(self.plon)
        f3['lsmlat']= np.atleast_1d(self.plat)
        f3['LATIXY'][:,:]= self.plat
        f3['LONGXY'][:,:]= self.plon

        #update attributes
        self.update_metadata(f3)
        f3.attrs['Created_from'] = self.fsurf_in
        del(f3.attrs['History_Log'])
        # mode 'w' overwrites file
        f3.to_netcdf(path=self.fsurf_out, mode='w')
        print('Successfully created file (fsurf_out) :'+self.fsurf_out)
        f2.close(); f3.close()

    def create_datmdomain_at_point(self):
        print( "----------------------------------------------------------------------")
        print("Creating DATM domain file at ", self.plon, self.plat, ".")
        # create 1d coordinate variables to enable sel() method
        filename = self.fdatmdomain_in
        f2 = self.create_1d_coord(filename, 'xc','yc','ni','nj')
        # extract gridcell closest to plon/plat
        f3 = f2.sel(ni=self.plon,nj=self.plat,method='nearest')
        # expand dimensions
        f3 = f3.expand_dims(['nj','ni'])
        wfile=self.fdatmdomain_out
        #update attributes
        self.update_metadata(f3)
        f3.attrs['Created_from'] = self.fdatmdomain_in
        # mode 'w' overwrites file
        f3.to_netcdf(path=wfile, mode='w')
        print('Successfully created file (fdatmdomain_out) :'+self.fdatmdomain_out)
        f2.close(); f3.close()

    def extract_datm_at(self, file_in, file_out):
        # create 1d coordinate variables to enable sel() method
        f2 = self.create_1d_coord(file_in, 'LONGXY','LATIXY','lon','lat')
        # extract gridcell closest to plon/plat
        f3  = f2.sel(lon=self.plon,lat=self.plat,method='nearest')
        # expand dimensions
        f3 = f3.expand_dims(['lat','lon'])
        # specify dimension order
        f3 = f3.transpose(u'scalar','time','lat','lon')

        #update attributes
        self.update_metadata(f3)
        f3.attrs['Created_from'] = file_in
        # mode 'w' overwrites file
        f3.to_netcdf(path=file_out, mode='w')
        print('Successfully created file :'+ file_out)
        f2.close(); f3.close()

    def create_datm_at_point(self):
        print( "----------------------------------------------------------------------")
        print("Creating DATM files at ", self.plon, self.plat, ".")
        #--  specify subdirectory names and filename prefixes
        solrdir = 'Solar/'
        precdir = 'Precip/'
        tpqwldir = 'TPHWL/'
        prectag = 'clmforc.GSWP3.c2011.0.5x0.5.Prec.'
        solrtag = 'clmforc.GSWP3.c2011.0.5x0.5.Solr.'
        tpqwtag = 'clmforc.GSWP3.c2011.0.5x0.5.TPQWL.'

        #--  create data files
        infile=[]
        outfile=[]
        for y in range(self.datm_syr,self.datm_eyr+1):
          ystr=str(y)
          for m in range(1,13):
             mstr=str(m)
             if m < 10:
                mstr='0'+mstr

             dtag=ystr+'-'+mstr

             fsolar=self.dir_input_datm+solrdir+solrtag+dtag+'.nc'
             fsolar2=self.dir_output_datm+solrtag+self.tag+'.'+dtag+'.nc'
             fprecip=self.dir_input_datm+precdir+prectag+dtag+'.nc'
             fprecip2=self.dir_output_datm+prectag+self.tag+'.'+dtag+'.nc'
             ftpqw=self.dir_input_datm+tpqwldir+tpqwtag+dtag+'.nc'
             ftpqw2=self.dir_output_datm+tpqwtag+self.tag+'.'+dtag+'.nc'

             infile+=[fsolar,fprecip,ftpqw]
             outfile+=[fsolar2,fprecip2,ftpqw2]

        nm=len(infile)
        for n in range(nm):
            print(outfile[n])
            file_in = infile[n]
            file_out = outfile[n]
            self.extract_datm_at(file_in, file_out)


        print('All DATM files are created in: '+self.dir_output_datm)


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
        sl = StreamToLogger(sys.stdout, stdout_logger, logging.INFO, also_log_to_stream)
        sys.stdout = sl

    @classmethod
    def setup_stderr(cls, also_log_to_stream=True):
        """
        Setup logger for stdout
        """
        stderr_logger = logging.getLogger('STDERR')
        sl = StreamToLogger(sys.stderr, stderr_logger, logging.ERROR, also_log_to_stream)
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
"""
Main
"""
################################################################################

def main ():

    args = get_parser().parse_args()

    # --------------------------------- #

    today = date.today()
    today_string = today.strftime("%Y%m%d")

    pwd = os.getcwd()

    log_file = os.path.join(pwd, today_string+'.log')

    log_level =  logging.DEBUG
    setup_logging(log_file, log_level)
    log = logging.getLogger(__name__)

    print("User = "+myname)
    print("Current directory = "+pwd)

    # --------------------------------- #

    if (args.run_type == "point"):
        print( "----------------------------------------------------------------------------")
        print( "This script extracts a single point from the global CTSM inputdata datasets." )

        #--  Specify point to extract
        plon = args.plon
        plat = args.plat

        #--  Create regional CLM domain file
        create_domain   = args.create_domain
        #--  Create CLM surface data file
        create_surfdata = args.create_surfdata
        #--  Create CLM surface data file
        create_landuse  = args.create_landuse
        #--  Create single point DATM atmospheric forcing data
        create_datm     = args.create_datm
        datm_syr = args.datm_syr
        datm_eyr = args.datm_eyr

        crop_flag = args.crop_flag

        site_name = args.site_name

        #--  Modify landunit structure
        overwrite_single_pft = args.overwrite_single_pft
        dominant_pft         = args.dom_pft
        zero_nonveg_landunits= args.zero_nonveg
        uniform_snowpack     = args.uni_snow
        no_saturation_excess = args.no_saturation_excess


        #--  Create SinglePoint Object
        single_point = SinglePointCase(plat, plon,site_name,
                            create_domain, create_surfdata, create_landuse, create_datm,
                            overwrite_single_pft, dominant_pft, zero_nonveg_landunits, uniform_snowpack,
                            no_saturation_excess)
        single_point.create_tag()


        print (single_point)

        if crop_flag:
            num_pft      = "78"
        else:
            num_pft      = "16"

        print('crop_flag = '+ crop_flag.__str__()+ ' => num_pft ='+ num_pft)

        #--  Set input and output filenames
        #--  Specify input and output directories
        dir_output = args.out_dir
        if ( not os.path.isdir( dir_output ) ):
            os.mkdir( dir_output )

        dir_inputdata='/glade/p/cesmdata/cseg/inputdata/'
        dir_clm_forcedata='/glade/p/cgd/tss/CTSM_datm_forcing_data/'
        dir_input_datm=os.path.join(dir_clm_forcedata,'atm_forcing.datm7.GSWP3.0.5d.v1.c170516/')
        dir_output_datm=os.path.join(dir_output , 'datmdata/')
        if ( not os.path.isdir( dir_output_datm ) ):
            os.mkdir( dir_output_datm )

        print ("dir_input_datm  : ", dir_input_datm)  #
        print ("dir_output_datm : ", dir_output_datm) #


        #--  Set time stamp
        today = date.today()
        timetag = today.strftime("%y%m%d")

        #--  Specify land domain file  ---------------------------------
        fdomain_in  = os.path.join(dir_inputdata,'share/domains/domain.lnd.fv0.9x1.25_gx1v7.151020.nc')
        fdomain_out = dir_output + single_point.add_tag_to_filename( fdomain_in, single_point.tag )
        single_point.fdomain_in = fdomain_in
        single_point.fdomain_out = fdomain_out
        print ("fdomain_in  :",fdomain_in)  #
        print ("fdomain_out :",fdomain_out) #

        #--  Specify surface data file  --------------------------------
        if crop_flag:
            fsurf_in = os.path.join (dir_inputdata, 'lnd/clm2/surfdata_map/release-clm5.0.18/surfdata_0.9x1.25_hist_78pfts_CMIP6_simyr2000_c190214.nc')
        else:
            fsurf_in = os.path.join (dir_inputdata, 'lnd/clm2/surfdata_map/release-clm5.0.18/surfdata_0.9x1.25_hist_16pfts_Irrig_CMIP6_simyr2000_c190214.nc')

        #fsurf_out  = dir_output + single_point.add_tag_to_filename(fsurf_in, single_point.tag) # remove res from filename for singlept
        fsurf_out   = dir_output + single_point.create_fileout_name(fsurf_in, single_point.tag)
        single_point.fsurf_in = fsurf_in
        single_point.fsurf_out = fsurf_out
        print ("fsurf_in   :",fsurf_in)  #
        print ("fsurf_out  :",fsurf_out) #

        #--  Specify landuse file  -------------------------------------
        if crop_flag:
            fluse_in = os.path.join (dir_inputdata,'lnd/clm2/surfdata_map/release-clm5.0.18/landuse.timeseries_0.9x1.25_hist_16pfts_Irrig_CMIP6_simyr1850-2015_c190214.nc')
        else:
            fluse_in = os.path.join (dir_inputdata,'lnd/clm2/surfdata_map/release-clm5.0.18/landuse.timeseries_0.9x1.25_hist_78pfts_CMIP6_simyr1850-2015_c190214.nc')
        #fluse_out   = dir_output + single_point.add_tag_to_filename( fluse_in, single_point.tag ) # remove resolution from filename for singlept cases
        fluse_out   = dir_output + single_point.create_fileout_name(fluse_in, single_point.tag)
        single_point.fluse_in = fluse_in
        single_point.fluse_out = fluse_out
        print ("fluse_in   :", fluse_in) #
        print ("fluse_out  :", fluse_out) #

        #--  Specify datm domain file  ---------------------------------
        fdatmdomain_in  = os.path.join (dir_clm_forcedata,'atm_forcing.datm7.GSWP3.0.5d.v1.c170516/domain.lnd.360x720_gswp3.0v1.c170606.nc')
        fdatmdomain_out = dir_output_datm+single_point.add_tag_to_filename( fdatmdomain_in, single_point.tag )
        single_point.fdatmdomain_in  = fdatmdomain_in
        single_point.fdatmdomain_out = fdatmdomain_out
        print ("fdatmdomain_in   : ", fdatmdomain_in)  #
        print ("fdatmdomain out  : ", fdatmdomain_out) #

        #--  Create CTSM domain file
        if create_domain:
            single_point.create_domain_at_point()

        #--  Create CTSM surface data file
        if create_surfdata:
            single_point.create_surfdata_at_point()

        #--  Create CTSM transient landuse data file
        if create_landuse:
            single_point.create_landuse_at_point()

        #--  Create single point atmospheric forcing data
        if create_datm:
            single_point.create_datmdomain_at_point()
            single_point.datm_syr =datm_syr
            single_point.datm_eyr =datm_eyr
            single_point.dir_input_datm = dir_input_datm
            single_point.dir_output_datm = dir_output_datm
            single_point.create_datm_at_point()

        print( "Successfully ran script for single point." )
        exit()

    else :
        # Print help when no option is chosen
        get_parser().print_help()

# Run :)
if __name__ == "__main__":
    main()
