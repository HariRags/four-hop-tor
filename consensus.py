# consensus.py - Functions to fetch and cache Tor consensus data
import stem.control
from stem.control import Controller
import os
import pickle
from datetime import datetime

def fetch_consensus():
    """Fetch the current consensus document with enhanced error handling."""
    print("Fetching Tor consensus... (this may take a minute)")
    
    # Check for recent cache
    cache_file = "tor_consensus_cache.pkl"
    if os.path.exists(cache_file):
        cache_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
        if (datetime.now() - cache_time).total_seconds() < 3600:  # Cache for 1 hour
            print("Using cached consensus data")
            with open(cache_file, 'rb') as f:
                consensus = pickle.load(f)
                if consensus and len(consensus) > 0:
                    print(f"Loaded {len(consensus)} relays from cache")
                    return consensus
                print("Cache was empty or corrupt, fetching fresh consensus")
    
    # First try using the controller to get the network status
    try:
        with Controller.from_port(port=9051) as controller:
            controller.authenticate()
            print("Successfully connected to control port, fetching consensus...")
            # Get network status entries directly from the controller
            consensus = list(controller.get_network_statuses())
            if consensus:
                print(f"Downloaded consensus with {len(consensus)} relays using Controller")
                # Cache the result
                with open(cache_file, 'wb') as f:
                    pickle.dump(consensus, f)
                return consensus
            else:
                print("Controller returned empty consensus, trying alternate method...")
    except Exception as e:
        print(f"Couldn't get consensus from controller: {e}")
        
    return []