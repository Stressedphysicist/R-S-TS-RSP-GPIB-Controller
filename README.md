# R&S TS-RSP GPIB Controller GUI
This is a very barebones GUI to enable switching of the different ports in a Rohde & Schwarz TS-RSP RF System Platform

- `app.py` is an API to control the TS-RSP via GPIB
- `gui.py` is a GUI inspired in the EMS-K1/ES-K1 software from Rohde & Schwarz
- `paths.json` is a json file that stores pre-configured paths for the TS-RSP

## Use

Install the required packages in `requirements.txt` and then:

Start the API 
```bash
uvicorn app:app --host 0.0.0.0 --port 8001
```

Open the GUI
```bash
python gui.py
```


