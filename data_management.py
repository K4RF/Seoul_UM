import json

DATA_FILE = 'data.json'

def save_data(data):
    with open(DATA_FILE, 'w') as file:
        json.dump(data, file)

def load_data():
    try:
        with open(DATA_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}