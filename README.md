# Create new single-point input forcing data for the NorESM land sites platform
## 1 Instructions

### 1.1 First time installation on SAGA
Log into SAGA and Run the following commands:
```
cd
git clone https://github.com/lasseke/nlp-input-handling.git
cd nlp-input-handling/install
chmod +x ./install_dependencies.sh
./install_dependencies.sh
```

## 2 Adding a new site
To print additional help, run `python3 create_forcing_classic.py --help`.

:warning: **You need to load the Python dependencies before you can create a new site!**
Run (note the dots!):
```
cd ~/nlp-input-handling
. ./load_dependencies.sh
```

#### 2.1 Add a single new site
Adapt the `site_instructions_template.yaml` file or use it as a template to create
a new one. Make sure it contains all the correct information concerning naming,
input data paths, etc. For example using vi:
```
vi site_input_instructions.yaml
...adapt content (press 'i' to edit and 'escape' when finished)...
:wq
```
Use the file as a recipe to create new compressed input via:
```
python3 create_forcing_classic.py -f [name_of_file].yml [-m [name_of_machine]]
```

#### 2.2 Add multiple new sites
Create a directory that will contain multiple `.yaml` recipes, for example:
```
mkdir mysites
```
Add as many instruction files using the `site_input_instructions.yaml` template
as you like into `mysites/` (following step 1.2.1).
Subsequently, run:
```
python3 create_forcing_classic.py -d ./mysites/ -m saga
```

## 3 Sending jobs to the SAGA queue
Check out the `make_input_jobscripts/` directory for template bash scripts that
will send the input data creation as jobs to the SAGA queue. Refer to [the SIGMA2 docs](https://documentation.sigma2.no/jobs/job_scripts.html) for additional information. Once you adapted a script
according to your needs and credentials, run the following command:
```
cd ~/nlp-input-handling/make_input_jobscripts
sbatch [my_script_name].sh
```