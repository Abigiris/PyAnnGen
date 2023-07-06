# (WIP) PyAnnGen 2.0

A tool for generating type annotations for Python, with new support for variables.

## Usage

Please follow these steps (and replace the file paths in all scripts with yours):

**Step1. use Pytype, Type4Py, and HiTyper to generate original type results, respectively**

Pytype: [https://github.com/google/pytype](https://github.com/google/pytype "https://github.com/google/pytype")

HiTyper: [https://github.com/JohnnyPeng18/HiTyper](https://github.com/JohnnyPeng18/HiTyper "https://github.com/JohnnyPeng18/HiTyper")

Type4Py: [https://github.com/saltudelft/type4py](https://github.com/saltudelft/type4py "https://github.com/saltudelft/type4py") or use our script (*/src/run_type4py.py*)

**Step2. Reformat these original results**

run the script */src/reformat_results.py*

**Step3. Run PyAnnGen**

run the script */src/PyAnnGen.py*


## Data

some examples of original results (/data/raw/\*), reformatted results (/data/std/\*) and final results of PyAnnGen (/data/std/types_\*)
