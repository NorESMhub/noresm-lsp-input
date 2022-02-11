# Create new single-point input forcing data for the NorESM land sites platform
## 1 Instructions

### 1.1 First time installation on SAGA
Log into SAGA and Run the following commands:
```
cd
git clone https://github.com/lasseke/nlp-input-handling.git
cd nlp-input-handling
./install_dependencies.sh
```

### 1.2 Adding a new site
To print additional help, run `python3 create_forcing_classic.py --help`.

#### 1.2.1 Add a single new site
Adapt the `site_input_instructions.yaml` file or use it as a template to create
a new one. Make sure it contains all the correct information concerning naming,
input data paths, etc. For example using vi:
```
vi site_input_instructions.yaml
...adapt content (press 'i' to edit and 'escape' when finished)...
:wq
```
Use the file as a recipe to create new compressed input via:
```
python3 create_forcing_classic.py -f [name_of_file].yml -m [name_of_machine]
```

#### 1.2.2 Add multiple new sites
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
