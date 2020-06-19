# Scone config generator

Generates a config for the scone enviroment, with the options of defining number of threads using hyperthreading and pinning threads to cores

Run the command as follow:
```[bash]
./generate.py -ht > sgx.config
```

And then set the enviorment ```SCONE_CONFIG``` variable to the ```sgx.config``` file.
```[bash]
export SCONE_CONFIG=sgx.config
```
