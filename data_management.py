import json

def save_data(data, file_path):
    with open(file_path, 'w') as file:
        json.dump(data, file)

def load_data(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}