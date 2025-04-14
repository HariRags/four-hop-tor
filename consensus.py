import stem.control
from stem.control import Controller
import os
import pickle
from datetime import datetime

def fetch_consensus():
    print("Fetching Tor consensus")
    try:
        with Controller.from_port(port=9051) as controller:
            controller.authenticate()
            consensus = list(controller.get_network_statuses())
            if consensus:
                print(f"Downloaded consensus with {len(consensus)} relays using Controller")
                return consensus
            else:
                print("Controller returned empty consensus")
    except Exception as e:
        print(f"Couldn't get consensus from controller: {e}")
    return []