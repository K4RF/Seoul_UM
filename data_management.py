import json

DATA_FILE = 'data.json'

def save_data(data):
    try:
        with open(DATA_FILE, 'w') as file:
            json.dump(data, file)
    except Exception as e:
        print(f"Error saving data: {e}")

def load_data():
    try:
        with open(DATA_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"Error loading data: {e}")
        return {}