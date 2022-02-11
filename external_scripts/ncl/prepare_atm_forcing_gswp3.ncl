load "$NCARG_ROOT/lib/ncarg/nclscripts/csm/contributed.ncl"
load "$NCARG_ROOT/lib/ncarg/nclscripts/csm/popRemap.ncl"
load "$NCARG_ROOT/lib/ncarg/nclscripts/esmf/ESMF_regridding.ncl"
load "$NCARG_ROOT/lib/ncarg/nclscripts/contrib/cd_string.ncl"

begin

  if (.not. isvar("plot_name")) then      ; is plot_name on command line?
    print("You must set the variable 'plot_name' via the command line! Example:")
    print("ncl 'plot_name=''SUB1''' file_name.ncl")
    print("OBS: the two single quotes around the command line string argument (-->''SUB1'') must be replaced by double quotes!")
    exit
  end if

  print ( "Beginning to create climate forcing files for: "+plot_name )

  if (.not. isvar("nc_in_file_path")) then      ; is nc_in_file_path on command line?
    print("You must provide a path to a aerdep nc file via the command line! Example:")
    print("ncl 'nc_in_file_path=''/cluster/shared/aero.nc''' file_name.ncl")
    print("OBS: the two single quotes around the command line string argument (-->''/cluster/...'') must be replaced by double quotes!")
    exit
  end if

  if (.not. isvar("out_file_path")) then      ; is out_file_path on command line?
    print("You must provide an output path for the new aerodep.nc file via the command line! Example:")
    print("ncl 'out_file_path=''/cluster/...''' file_name.ncl")
    print("OBS: the two single quotes around the command line string argument (-->''/cluster/...'') must be replaced by double quotes!")
    exit
  end if

  if (.not. isvar("plot_lat")) then      ; is plot_lat on command line?
    print("You must provide a plot lat value via the command line! Example:")
    print("ncl plot_lon=60.94231 file_name.ncl")
    exit
  end if

  if (.not. isvar("plot_lon")) then      ; is plot_lon on command line?
    print("You must provide a plot lon value via the command line! Example:")
    print("ncl plot_lon=6.52332 file_name.ncl")
    exit
  end if

  if (.not. isvar("year_start")) then      ; is year_start on command line?
    print("You must provide a start year value via the command line! Example:")
    print("ncl year_start=1901 file_name.ncl")
    exit
  end if

  if (.not. isvar("year_end")) then      ; is year_end on command line?
    print("You must provide an end year value via the command line! Example:")
    print("ncl year_end=2010 file_name.ncl")
    exit
  end if

   ;out_file_path   = "/cluster/shared/noresm/inputdata_fates_platform/atm/datm7/GSWP3v1/"+plot_name+"/"
   ;nc_in_file_path    = "/cluster/shared/noresm/inputdata/atm/datm7/atm_forcing.datm7.GSWP3.0.5d.v1.c170516/"

   mon = ispan(0,11,1)
   mon@units  = "month"
   month =cd_string(mon,"%N")

   xfloor=plot_lon-0.005
   xceil =plot_lon+0.005
   yfloor=plot_lat-0.005
   yceil =plot_lat+0.005
   print(yceil)
   print(xceil)

   do year=year_start,year_end,1
      do m=0,11,1

         frsds=addfile(nc_in_file_path+"/Solar/clmforc.GSWP3.c2011.0.5x0.5.Solr."+year+"-"+month(m)+".nc","r")
         fprec=addfile(nc_in_file_path+"/Precip/clmforc.GSWP3.c2011.0.5x0.5.Prec."+year+"-"+month(m)+".nc","r")
         ftphw=addfile(nc_in_file_path+"/TPHWL/clmforc.GSWP3.c2011.0.5x0.5.TPQWL."+year+"-"+month(m)+".nc","r")

         rsds=frsds->FSDS(:,:,:)
         prec=fprec->PRECTmms(:,:,:)
         psrf=ftphw->PSRF(:,:,:)
         tbot=ftphw->TBOT(:,:,:)
         wind=ftphw->WIND(:,:,:)
         qbot=ftphw->QBOT(:,:,:)
         flds=ftphw->FLDS(:,:,:)

         lon=frsds->LONGXY(0,:)
         lat=frsds->LATIXY(:,0)
         time=frsds->time(:)
         edgew   =frsds->EDGEW
         edgee   =frsds->EDGEE
         edges   =frsds->EDGES
         edgen   =frsds->EDGEN
         longxy  =frsds->LONGXY
         latixy  =frsds->LATIXY

         loni=ind_nearest_coord(plot_lon, lon, 0)
         latj=ind_nearest_coord(plot_lat, lat, 0)
         print(loni)
         print(latj)

;########## Creat forcing in netcdf format

         system("rm -f "+out_file_path+"clm1pt_"+plot_name+"_"+year+"-"+month(m)+".nc")    ; remove if exists
         fclim  = addfile(out_file_path+"clm1pt_"+plot_name+"_"+year+"-"+month(m)+".nc","c")
         ntim  = dimsizes(time)                 ; get dimension sizes
         nlat  = 1
         nlon  = 1
         nscalar = 1

         setfileoption(fclim,"DefineMode",True)

         fAtt               = True            ; assign file attributes
         fAtt@case_title    = "GSWP3v1: norway "
         fAtt@conventions   = "CF-1.0"
         fAtt@title         = "CLM single point datm input data"
         fAtt@history       = "Original data from GSWP3v1 data"
         fAtt@creation_date = systemfunc ("date")
         fileattdef( fclim, fAtt )            ; copy file attributes

         dimNames = (/"scalar","lon","lat","time"/)
         dimSizes = (/ nscalar, nlon, nlat, -1 /)
         dimUnlim = (/ False, False, False, True/)
         filedimdef(fclim,dimNames,dimSizes,dimUnlim)

         filevardef(fclim, "EDGEW" ,typeof(edgew),getvardims(edgew))
         filevardef(fclim, "EDGEE"  ,typeof(edgee),getvardims(edgee))
         filevardef(fclim, "EDGES"  ,typeof(edges),getvardims(edges))
         filevardef(fclim, "EDGEN"  ,typeof(edgen),getvardims(edgen))
         filevardef(fclim, "LONGXY" ,typeof(longxy)  ,getvardims(longxy))
         filevardef(fclim, "LATIXY"  ,typeof(latixy) ,getvardims(latixy))
         filevardef(fclim, "time",typeof(time),getvardims(time))
         filevardef(fclim, "FSDS",typeof(rsds),getvardims(rsds))
         filevardef(fclim, "PRECTmms",typeof(prec),getvardims(prec))
         filevardef(fclim, "TBOT",typeof(tbot),getvardims(tbot))
         filevardef(fclim, "WIND",typeof(wind),getvardims(wind))
         filevardef(fclim, "PSRF",typeof(psrf),getvardims(psrf))
         filevardef(fclim, "QBOT",typeof(qbot),getvardims(qbot))
         filevardef(fclim, "FLDS",typeof(flds),getvardims(flds))

         filevarattdef(fclim,"EDGEW",edgew)
         filevarattdef(fclim,"EDGEE",edgee)
         filevarattdef(fclim,"EDGES",edges)
         filevarattdef(fclim,"EDGEN",edgen)
         filevarattdef(fclim,"LONGXY",longxy)
         filevarattdef(fclim,"LATIXY",latixy)
         filevarattdef(fclim,"time",time)
         filevarattdef(fclim,"FSDS",rsds)
         filevarattdef(fclim,"PRECTmms",prec)
         filevarattdef(fclim,"TBOT",tbot)
         filevarattdef(fclim,"WIND",wind)
         filevarattdef(fclim,"PSRF",psrf)
         filevarattdef(fclim,"QBOT",qbot)
         filevarattdef(fclim,"FLDS",flds)

         setfileoption(fclim,"DefineMode",False)

         print(time)
         fclim->time   = (/time/)        ; "(/", "/)" syntax tells NCL to only output the data values to the predefined locations on the file.
         fclim->EDGEW  = (/xfloor/)
         fclim->EDGEE  = (/xceil/)
         fclim->EDGES  = (/yfloor/)
         fclim->EDGEN  = (/yceil/)
         fclim->LONGXY = (/plot_lon/)
         fclim->LATIXY  = (/plot_lat/)
         fclim->FSDS   = (/rsds(:,latj,loni)/)
         fclim->PRECTmms   = (/prec(:,latj,loni)/)         ; !!!! time variable can be modified in the attributes of the variable is also copied. make sure to use (/ /) to only copy data.
         fclim->TBOT   = (/tbot(:,latj,loni)/)
         fclim->WIND   = (/wind(:,latj,loni)/)
         fclim->PSRF   = (/psrf(:,latj,loni)/)
         fclim->QBOT   = (/qbot(:,latj,loni)/)
         fclim->FLDS   = (/flds(:,latj,loni)/)

         delete(time)
         delete(rsds)
         delete(prec)
         delete(tbot)
         delete(qbot)
         delete(wind)
         delete(psrf)
         delete(flds)

      end do
   end do
end
