import yaml

with open(r"C:\Git_repos\nlp-input-handling\site_input_instructions.yaml", 'r') as stream:
    dictionary = yaml.safe_load(stream)
for key, value in dictionary.items():
    print (key + " : " + str(value))