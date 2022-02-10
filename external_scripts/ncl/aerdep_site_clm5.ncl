;
; Create site/regional aerosol deposition file for the model platform
; The origional global file used by default is too large.
; This script is adapated from the original "aerdepregrid.ncl" used in early versions of CLM (see below the original statement)
;
;;#####################################################
;; Regrid CLM Aerosol-Deposition file (aerdep) to a new resolution.
;; Works for climatology monthly aerdep files.
;; Uses input environment variables to determine resolution and other
;; parameters to describe set of files to use.
;; Uses bld query to get input filenames. Also uses env variable CSMDATA for location
;; of input files.
;;
;;  Erik Kluzek
;;  Apr/10/2008
;;  $Id: aerdepregrid.ncl 28400 2011-05-16 05:46:46Z erik $
;;  $HeadURL;
;;######################################################

begin
  ; ===========================================================================================================
  ;
  ; IMPORTANT NOTE: EDIT THE FOLLOWING TO CUSTOMIZE
  ; Edit the following as needed to interpolate to a new resolution.
  ; Input and output resolution

;################
;Setup begin
;################

  if (.not. isvar("plot_name")) then      ; is plot_name on command line?
    print("You must set the variable 'plot_name' via the command line! Example:")
    print("ncl 'plot_name=''SUB1''' file_name.ncl")
    print("OBS: the two single quotes around the command line string argument (-->''SUB1'') must be replaced by double quotes!")
    exit
  end if

  print ( "Beginning to build aerdep file for: "+plot_name )

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

  if (.not. isvar("out_file_path")) then      ; is out_file_path on command line?
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

  ; Open files
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
  dimnames  = (/ "time", "lat", "lon", "ntb" /);
  latgg     = ncg->yc(:,0);
  longg     = ncg->xc(0,:);
  nlat      = dimsizes( latgg );
  nlon      = dimsizes( longg );
  ntime     = getfilevardimsizes(nc,"time");
  dsizes    = (/ ntime, nlat,  nlon, 2 /);
  is_unlim  = (/ True,  False, False, False /);
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
  nco@aerdepregridRevision = "$Id: aerdepregrid.ncl 28400 2011-05-16 05:46:46Z erik $";
  ;
  ; Copy coordinate variables over
  ;
  if ( isfilevar( nc, "date" ) ) then
     nco->date= (/nc->date/);
  end if
  if ( isfilevar( nc, "time" ) ) then
     nco->time= (/nc->time/);
  end if
  nco->lon   = doubletofloat( (/longg/) );
  nco->lat   = doubletofloat( (/latgg/) );
  nco->time_bnds   = (/nc->time_bnds/);
  nco->datesec   = (/nc->datesec/);
  lon  = (/ nc->lon /);
  lat  = (/ nc->lat /);
  lono = (/ nco->lon /);
  lato = (/ nco->lat /);


  areao   = doubletofloat( (/ ncg->area /) );
  sumarea = sum(areao);
  areao   = areao / sumarea;

  ;
  ; loop over variables
  ;
  if ( nlon .eq. 1 )then
     Cyclic = False
  else
     dx = lono(1) - lono(0);
     ; The last longitude should equal 360-(dx-first_longitude)
     ; So for example if first_longitude=0,  last will be 360-dx
     ;                If first_longitude=dx, last will be 360
     expLast = 360.0 - (dx - lono(0));
     if ( abs(lono(nlon-1) - expLast) .lt. 1.e-4 )then
        Cyclic = True;
     else
        Cyclic = False
     end if
  end if

  print( "Cyclic grid: "+Cyclic );

  do i = 0, dimsizes( vars )-1

     vardimnames = getfilevardims( nc, vars(i) );
     ;
     ; If variable is not one of the dimensions -- regrid it and write to output file
     ;
     if ( (vars(i) .ne. "date") .and. (vars(i) .ne. "time") .and. (vars(i) .ne. "lat") .and. (vars(i) .ne. "lon") .and. (vars(i) .ne. "datesec").and. (vars(i) .ne. "time_bnds"))then
       print( "Write variable: "+vars(i)+" to output file" );
       ;
       ; If time dimension
       ;
       if ( vardimnames(0) .eq. "time" )then
          do t = 0, ntime-1
             vart  = (/nc->$vars(i)$(t,:,:)/);
             varto = linint2 ( lon,  lat,  vart, Cyclic, lono, lato, 0 );
             if ( all(ismissing(varto(nlat-1,:))) )then
                print( "Copy last latitude over" );
                varto(nlat-1,:) = varto(nlat-2,:);
             end if
             if ( any(ismissing(varto)) )then
                print( "There are some missing values on output no="+num(ismissing(varto)) );
                exit
             end if
             nco->$vars(i)$(time|t,lat|:,lon|:) = (/varto/);
             varto = varto*areao;
          end do
       ;
       ; without time dimension
       ;
       else
          var  = (/nc->$vars(i)$/);
          varo = linint2 ( lon, lat,  var, Cyclic, lono, lato, 0 );
          if ( all(ismissing(varo(nlat-1,:))) )then
             print( "Copy last latitude over" );
             varo(nlat-1,:) = varo(nlat-2,:);
          end if
          if ( any(ismissing(varo)) )then
             print( "There are some missing values on output no="+num(ismissing(varo)) );
             exit
          end if
          nco->$vars(i)$ = (/varo/);
          varo = varo*areao;
       end if
     end if
     delete( vardimnames );

  end do
  if ( isvar("varto") )then
     delete(varto);
  end if
  if ( isvar("vart") )then
     delete(vart);
  end if
  delete(areao);
  if ( isvar("varo") )then
     delete(varo);
  end if
  if ( isvar("var") )then
     delete(var)
  end if

  print( "================================================================================================" );
  print( "Successfully created output aerdep file: "+out_file_path );

end
