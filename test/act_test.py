import json
import os


def get_mock_data(filename):
    dirname = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dirname, filename), "r") as f:
        return json.loads(f.read())
