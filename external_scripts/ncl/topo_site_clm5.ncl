;
; Create site elevation file to be read by DATM
;
;  Hui Tang
;  08/2020
;

begin

;################
;Setup begin
;################

  if (.not. isvar("plot_name")) then      ; is plot_name on command line?
    print("You must set the variable 'plot_name' via the command line! Example:")
    print("ncl 'plot_name=''SUB1''' file_name.ncl")
    print("OBS: the two single quotes around the command line string argument (-->''SUB1'') must be replaced by double quotes!")
    exit
  end if

  print( "Creating topography for: "+plot_name )

  if (.not. isvar("plot_height")) then      ; is plot_name on command line?
    print("You must set the variable 'plot_height' (-> site elevation) via the command line! Example:")
    print("ncl plot_height=900 file_name.ncl")
    exit
  end if

  if (.not. isvar("nc_in_file_path")) then      ; is nc_in_file_path on command line?
    print("You must provide a path to a aerdep nc file via the command line! Example:")
    print("ncl 'nc_in_file_path=''/cluster/shared/aero.nc''' file_name.ncl")
    print("OBS: the two single quotes around the command line string argument (-->''/cluster/...'') must be replaced by double quotes!")
    exit
  end if

  nc_in_file_path_split = str_split(nc_in_file_path, "/")
  nc_in_split_len = dimsizes(nc_in_file_path_split)
  nc_in_file_name = nc_in_file_path_split(nc_in_split_len-1)
  nc_in_file_name_no_suffix = str_sub_str(nc_in_file_name, ".nc", "") ; Remove .nc ending

  if (.not. isvar("out_file_path")) then      ; is nyrStrt on command line?
    print("You must provide an output path for the new aerodep.nc file via the command line! Example:")
    print("ncl 'out_file_path=''/cluster/...''' file_name.ncl")
    print("OBS: the two single quotes around the command line string argument (-->''/cluster/...'') must be replaced by double quotes!")
    exit
  end if

  out_file_path = out_file_path+nc_in_file_name_no_suffix+"_"+plot_name+".nc"

  if (.not. isvar("domain_file_path")) then      ; is domain file path on command line?
    print("You must provide a domain file path via the command line! Example:")
    print("ncl 'domain_file_path=''/cluster/...''' file_name.ncl")
    print("OBS: the two single quotes around the command line string argument (-->''/cluster/...'') must be replaced by double quotes!")
    exit
  end if

;################
;Setup end
;################
    ;
    ; Open files
    ;
    print( "Interpolate from file: "+nc_in_file_path );
    if ( systemfunc("test -f "+nc_in_file_path+"; echo $?" ) .ne. 0 )then
       print( "Input faerdep file does not exist or not found: "+nc_in_file_path );
       exit
    end if
  nc       = addfile( nc_in_file_path,    "r" );

  print( "Use grid file:         "+domain_file_path );
  if ( systemfunc("test -f "+domain_file_path+"; echo $?" ) .ne. 0 )then
     print( "Input domain_file_path does not exist or not found: "+domain_file_path );
     exit
  end if
  ncg      = addfile( domain_file_path,    "r" );
  print( "Output file:           "+out_file_path );
  if ( systemfunc("test -f "+out_file_path+"; echo $?" ) .eq. 0 )then
     system( "/bin/rm -f "+out_file_path );
  end if
  nco      = addfile( out_file_path, "c" );
  ;
  ; Define dimensions
  ;
  dimnames  = (/ "time", "lat", "lon" /);
  latgg     = ncg->yc(:,0);
  longg     = ncg->xc(0,:);
  nlat      = dimsizes( latgg );
  nlon      = dimsizes( longg );
  ntime     = getfilevardimsizes(nc,"time");
  dsizes    = (/ ntime, nlat,  nlon /);
  is_unlim  = (/ True,  False, False /);
  filedimdef( nco, dimnames, dsizes, is_unlim );
  print( "Number of times: "+ntime );
  ;
  ; Define vars and add attributes from original file
  ;
  print( "Define vars" );
  vars = getfilevarnames( nc );
  print(vars)
  i = dimsizes(vars) - 1
  do while ( i .ge. 0 )
     print( "Define "+vars(i) );
     filevardef (    nco, vars(i), typeof(nc->$vars(i)$), getfilevardims( nc, vars(i) ) );
     filevarattdef ( nco, vars(i), nc->$vars(i)$ );
     i = i - 1
  end do
  fileattdef ( nco, nc );
  ;
  ; Add global attributes to output file
  ;
  print( "Global attributes" );

  nco@source               = "Regrid from:"+nc_in_file_path;
  nco@domain_file_path             = domain_file_path;
  nco@aerdepregridVersion  = "$HeadURL: https://svn-ccsm-models.cgd.ucar.edu/clm2/branch_tags/cesm1_0_rel_tags/cesm1_0_3_n05_clm4_0_32/models/lnd/clm/tools/ncl_scripts/aerdepregrid.ncl $";

  ;
  ; Copy coordinate variables over
  ;

  if ( isfilevar( nc, "time" ) ) then
     nco->time   = (/nc->time/);
  end if
  if ( isfilevar( nc, "mask" ) ) then
     nco->mask   = (/ncg->mask/);
  end if
  if ( isfilevar( nc, "area" ) ) then
     nco->area   = (/ncg->area/);
  end if
  if ( isfilevar( nc, "NUMLON" ) ) then
     nco->NUMLON = (/nlon/);
  end if
  nco->LONGXY    = (/ncg->xc(:,:)/);
  nco->LATIXY    = (/ncg->yc(:,:)/);
  nco->TOPO      = (/plot_height/);


  print( "================================================================================================" );
  print( "Successfully created output aerdep file: "+out_file_path );

end
