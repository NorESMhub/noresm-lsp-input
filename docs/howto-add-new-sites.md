# Adding a new site to the platform (for developer docs)
## 1 Create single-point input data from global files
This step is currently only implemented and tested for execution on the Norwegian cluster HPCs  SAGA/FRAM. Porting the code somewhere else is possible, but requires some level of technical expertise and adaptations.

**Warning**: creating the input data requires sufficient computational resources (tested for 16 GB of memory + 10 cores) and available storage disk space (each new site will create a raw output of ~16GB, which can be deleted afterwards). We highly recommend not running the following instructions in your personal login-node $HOME area but in $USERWORK and as a job sent to the queue instead.

1. Log into SAGA:
```
ssh [user-name]@saga.sigma2.no
```
2. Change directory to an appropriate target root for the scripts (see warning above). Recommended:
```
cd $USERWORK
```
3. Clone the input data creation repository:
```
git clone https://github.com/lasseke/noresm-lsp-input
```

4. Follow the installation steps in `[local_path]/noresm-lsp-input/README.md`.
Before running the code for a new site instruction “.yaml” file, make sure:
- that the installation scripts use correct paths, links, and GitHub release tags
- that the paths in the “.yaml” are absolute (i.e., not bash $VAR notation)
- that the NetCDF files (*.nc) you want to subset in fact exist in the specified directory, otherwise you can likely download them from https://svn-ccsm-inputdata.cgd.ucar.edu/trunk/inputdata/ 

5. Follow the example scripts contained in `[local_path]/nlp-input-handling/make_input_jobscripts/[version]/` to send the input creation as a new job to the SAGA queue. You can then check the progress via `squeue -u [your_username]`. An “R” under “ST” indicates that the job is running.

6. Check the `slurm-[your-job-id].out` file (in the folder where you started the job) for logs and potential errors.

With the recommended specifications, you can expect a single job to run for ~3-6 hours.

## 2 Upload the new input data tarball to NIRD
Use a file transfer option of your choice (WinSCP, etc.) to move the newly created “.tar” archive to the NIRD storage. Make sure to place it in the correct subfolder (version, etc.). For instance:
```
scp inputdata_version1.0.0_[your-site-id].tar [your-user-name]@login.nird.sigma2.no:/projects/NS2806K/EMERALD/EMERALD_platform/inputdata_noresm_landsites/v1.0.0/default/`
```

## 3 Add the new site to the ctsm/noresm-lsp config files (for v1.0.0)
Currently (v1.0.0), you need to carefully hardcode new sites into different files within the noresm-lsp structure. See https://github.com/NorESMhub/NorESM_LandSites_Platform/pull/116 for an example, but details are also described below:
1. Clone (or fork) the noresm-land-sites-platform repository and create a new branch:
```
git clone https://github.com/NorESMhub/noresm-land-sites-platform.git
git checkout -b [new-branch-name]
```
2. In `resources/config/sites.json`:
→ Copy an existing GEOJSON entry (everything between the curly brackets that starts before “type”: ”Feature”) and adapt the coordinates, download url, fsurfdat, group, … values. IT MUST MATCH THE ASSOCIATED “.yaml” INFORMATION AND STORAGE URL FOR YOUR NEW SITE!

3. In `resources/overwrites/ccs_config/component_grids_nuopc.xml`, add (see examples around line 655):
```
<domain name="1x1_[your-site-id]">
<lat>[your-site-lat-coordinate]</lat> 
<lon>[your-site-lon-coordinate]</lon>
<desc>[your-description] -- only valid for DATM/CLM compset</desc>
</domain>
```

4. In `resources/overwrites/ccs_config/modelgrid_aliases_nuopc.xml`, add (see examples around line 137):
```
<model_grid alias="1x1_[your-site-id]" compset="DATM.+CLM|DATM.+SLND">
<grid name="atm">1x1_[your-site-id]</grid>
<grid name="lnd">1x1_[your-site-id]</grid>
<grid name="rof">null</grid>
</model_grid>
```

5. In `resources/overwrites/components/cdeps/datm/cime_config/namelist_definition_datm.xml`, add (see examples around line 82):
```
<value datm_mode="CLM1PT" model_grid="1x1_[your-site-id]">
CLM1PT.$ATM_GRID.Solar,CLM1PT.$ATM_GRID.Precip,CLM1PT.$ATM_GRID.TPQW
</value>
```

6. In `resources/overwrites/components/cdeps/datm/cime_config/stream_definition_datm.xml`, add (see examples around line 1445):

```
<stream_entry name="CLM1PT.1x1_[your-site-id].Solar">
	<stream_meshfile>
		<meshfile>none</meshfile>
	</stream_meshfile>
	<stream_datafiles>
		<file first_year="1901" last_year="2014">$DIN_LOC_ROOT_CLMFORC/[your-site-id]/clm1pt_[your-site-id]_%ym.nc</file>
	</stream_datafiles>
	<stream_datavars>
		<var>FSDS Faxa_swdn</var>
	</stream_datavars>
	<stream_lev_dimname>null</stream_lev_dimname>
	<stream_mapalgo>
		<mapalgo>none</mapalgo>
	</stream_mapalgo>
	<stream_vectors>null</stream_vectors>
	<stream_year_align>$DATM_YR_ALIGN</stream_year_align>
	<stream_year_first>$DATM_YR_START</stream_year_first>
	<stream_year_last>$DATM_YR_END</stream_year_last>
	<stream_offset>0</stream_offset>
	<stream_tintalgo>
		<tintalgo>coszen</tintalgo>
	</stream_tintalgo>
	<stream_taxmode>
		<taxmode>cycle</taxmode>
		<taxmode compset="HIST">limit</taxmode>
	</stream_taxmode>
	<stream_dtlimit>
		<dtlimit>1.5</dtlimit>
	</stream_dtlimit>
	<stream_readmode>single</stream_readmode>
</stream_entry>

<stream_entry name="CLM1PT.1x1_[your-site-id].Precip">
	<stream_meshfile>
		<meshfile>none</meshfile>
	</stream_meshfile>
	<stream_datafiles>
		<file first_year="1901" last_year="2014">$DIN_LOC_ROOT_CLMFORC/[your-site-id]/clm1pt_[your-site-id]_%ym.nc</file>
	</stream_datafiles>
	<stream_datavars>
		<var>PRECTmms Faxa_precn</var>
	</stream_datavars>
	<stream_lev_dimname>null</stream_lev_dimname>
	<stream_mapalgo>
		<mapalgo>none</mapalgo>
	</stream_mapalgo>
	<stream_vectors>null</stream_vectors>
	<stream_year_align>$DATM_YR_ALIGN</stream_year_align>
	<stream_year_first>$DATM_YR_START</stream_year_first>
	<stream_year_last>$DATM_YR_END</stream_year_last>
	<stream_offset>5400</stream_offset>
	<stream_tintalgo>
		<tintalgo>nearest</tintalgo>
	</stream_tintalgo>
	<stream_taxmode>
		<taxmode>cycle</taxmode>
		<taxmode compset="HIST">limit</taxmode>
	</stream_taxmode>
	<stream_dtlimit>
		<dtlimit>1.5</dtlimit>
	</stream_dtlimit>
	<stream_readmode>single</stream_readmode>
</stream_entry>

<stream_entry name="CLM1PT.1x1_[your-site-id].TPQW">
	<stream_meshfile>
		<meshfile>none</meshfile>
	</stream_meshfile>
	<stream_datafiles>
		<file first_year="1901" last_year="2014">$DIN_LOC_ROOT_CLMFORC/[your-site-id]/clm1pt_[your-site-id]_%ym.nc</file>
	</stream_datafiles>
	<stream_datavars>
		<var>TBOT     Sa_tbot</var>
		<var>WIND     Sa_wind</var>
		<var>QBOT     Sa_shum</var>
		<var>PSRF     Sa_pbot</var>
		<var>FLDS     Faxa_lwdn</var>
	</stream_datavars>
	<stream_lev_dimname>null</stream_lev_dimname>
	<stream_mapalgo>
		<mapalgo>none</mapalgo>
	</stream_mapalgo>
	<stream_vectors>null</stream_vectors>
	<stream_year_align>$DATM_YR_ALIGN</stream_year_align>
	<stream_year_first>$DATM_YR_START</stream_year_first>
	<stream_year_last>$DATM_YR_END</stream_year_last>
	<stream_offset>5400</stream_offset>
	<stream_tintalgo>
		<tintalgo>linear</tintalgo>
	</stream_tintalgo>
	<stream_taxmode>
		<taxmode>cycle</taxmode>
		<taxmode compset="HIST">limit</taxmode>
	</stream_taxmode>
	<stream_dtlimit>
		<dtlimit>1.5</dtlimit>
	</stream_dtlimit>
	<stream_readmode>single</stream_readmode>
</stream_entry>
```
7. In `resources/overwrites/components/clm/bld/namelist_files/namelist_defaults_ctsm.xml`, add (see examples around lines 903, 1371, 1385, 1457):

```
<fsurdat hgrid="1x1_[your-site-id]" sim_year="2000" use_crop=".false." irrigate=".true.">
lnd/clm2/surfdata_map/-[your-site-id]/surfdata_[your-site-id]_simyr2000.nc</fsurdat>
<fsurdat hgrid="48x96" sim_year="2000" use_crop=".false." irrigate=".true.">

[...]

<stream_fldfilename_lightng hgrid="1x1_[your-site-id]">atm/datm7/NASA_LIS/[your-site-id]/clmforc.Li_2016_climo1995-2013.360x720.lnfm_Total_c160825_[your-site-id].nc</stream_fldfilename_lightng>

[...]

<lightngmapalgo hgrid="1x1_[your-site-id]">nn</lightngmapalgo>

[...]

<stream_fldfilename_popdens hgrid="1x1_[your-site-id]" use_fates=".true.">lnd/clm2/firedata/[your-site-id]/clmforc.Li_2017_HYDEv3.2_CMIP6_hdm_0.5x0.5_AVHRR_simyr1850-2016_c180202_[your-site-id].nc</stream_fldfilename_popdens>

[...]

<stream_fldfilename_urbantv phys="clm5_0" hgrid="1x1_[your-site-id]">lnd/clm2/urbandata/[your-site-id]/CLM50_tbuildmax_Oleson_2016_0.9x1.25_simyr1849-2106_c160923_[your-site-id].nc</stream_fldfilename_urbantv>
```

8. To test the changes locally:
- Stop potentially running noresm-lsp containers
- Delete the `resources/ctsm` dir
- Run `docker-compose up` to start the container as usual → this will reclone CTSM and apply the changes you made in the `overwrites` dir

9. Once you made sure everything works, you can push your changes and/or create a pull request (PR) on GitHub.

_The end._
