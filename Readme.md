## How to run Vizop from source (Windows 10)

* Install **[Python 3.7.x](https://www.python.org/downloads/)**

* Do not forget to tick "Add to path" checkbox at installation, otherwise add the following paths to current user PATH environment variable:

    * `C:\Users\{username}\AppData\Local\Programs\Python37`
    * `C:\Users\{username}\AppData\Local\Programs\Python37\Scripts`

* Install [`virtualenv`](https://www.dabapps.com/blog/introduction-to-pip-and-virtualenv-python/) to keep each project libraries versions independent. Open a command prompt as administrator, then run `pip install virtualenv`.

* Go to Vizop project root and set environment directory to `env` by typing `virtualenv env` (note that `env` directory is already listed in file `.gitignore`).

* Switch to local Python & Pip commands: run `env\Scripts\activate.bat` 

* Install required libraries:
```
pip install wxPython==4.0.7.post2
pip install pyzmq
pip install openpyxl
```

* Lauch Vizop: `python vizop.py`