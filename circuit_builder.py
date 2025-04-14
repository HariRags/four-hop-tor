# circuit_builder.py - Functions for building, testing, and maintaining Tor circuits
import time
import stem.control
import socks
from consensus import fetch_consensus
from relay_classification import classify_relays
from relay_selection import select_guard, select_middle, select_exit

def generate_circuit(num_hops=4):
    """Generate a circuit with the specified number of hops."""
    consensus = fetch_consensus()
    
    if not consensus or len(consensus) == 0:
        print("Failed to fetch consensus data")
        return []
        
    relays = classify_relays(consensus)
    
    circuit = []
    
    # First hop is always a guard
    guard = select_guard(relays)
    if guard:
        circuit.append(guard)
    else:
        print("Failed to select a guard node")
        return []
    
    # Middle hops (can be any non-exit relay)
    for i in range(num_hops - 2):
        middle = select_middle(relays, circuit)
        if middle:
            circuit.append(middle)
        else:
            print(f"Failed to select middle node {i+2}")
            return []
    
    # Last hop is an exit
    exit = select_exit(relays, circuit)
    if exit:
        circuit.append(exit)
    else:
        print("Failed to select an exit node")
        return []
    
    return circuit

def build_custom_circuit(controller, hops=4):
    """Build a custom circuit with the specified number of hops."""
    # Generate our custom path
    circuit_path = generate_circuit(hops)
    
    if not circuit_path or len(circuit_path) < hops:
        print(f"Failed to generate a complete {hops}-hop circuit")
        return None, circuit_path
        
    # Format path for circuit creation
    path_fingerprints = [relay.fingerprint for relay in circuit_path]
    
    print(f"\nBuilding {hops}-hop circuit:")
    for i, relay in enumerate(circuit_path):
        print(f"Hop {i+1}: {relay.nickname} ({relay.fingerprint}) - {relay.address}:{relay.or_port}")
    
    # Create the circuit
    try:
        circuit_id = controller.new_circuit(path_fingerprints, await_build=True)
        print(f"\nCircuit {circuit_id} built successfully!")
        return circuit_id, circuit_path
    except Exception as e:
        print(f"Failed to build circuit: {e}")
        return None, circuit_path

def test_circuit(controller, circuit_id):
    """Test if the circuit works by making a connection through it."""
    if not circuit_id:
        print("No circuit to test")
        return False
    
    try:
        # First, tell Tor to use this controller for stream management
        controller.set_conf('__LeaveStreamsUnattached', '1')
        
        # Create a listener for stream events
        print("Setting up stream listener...")
        stream_listener_ready = False
        
        def attach_stream(stream):
            if stream.status == 'NEW' and stream.purpose == 'USER':
                try:
                    controller.attach_stream(stream.id, circuit_id)
                    print(f"Attached stream {stream.id} to our circuit {circuit_id}")
                    return True
                except Exception as e:
                    print(f"Failed to attach stream: {e}")
            return False
        
        # Add the stream listener
        controller.add_event_listener(attach_stream, stem.control.EventType.STREAM)
        
        # Now make a connection through Tor's SOCKS port
        import socket
        import socks
        
        # Configure a socket to use Tor's SOCKS port
        print("Creating connection through Tor SOCKS port...")
        s = socks.socksocket()
        s.set_proxy(socks.SOCKS5, "127.0.0.1", 9050)
        
        try:
            # This connection will be intercepted and attached to our circuit
            print("Connecting to check.torproject.org...")
            s.connect(("check.torproject.org", 80))
            s.send(b"GET / HTTP/1.1\r\nHost: check.torproject.org\r\n\r\n")
            
            # Read the first part of the response to verify it worked
            response = s.recv(1024)
            if response:
                print("Successfully received data through the circuit:")
                print(response[:100].decode('utf-8', errors='ignore'))
                s.close()
                print("Connection test successful!")
                return True
            else:
                print("Connection succeeded but received no data")
                s.close()
                return False
                
        except Exception as e:
            print(f"Error testing connection: {e}")
            return False
        finally:
            # Clean up
            controller.remove_event_listener(attach_stream)
            controller.reset_conf('__LeaveStreamsUnattached')
            
    except Exception as e:
        print(f"Failed to test circuit: {e}")
        return False

def build_circuit_with_retry(controller, hops=4, max_attempts=5):
    """Try to build a circuit, retrying with different relays if it fails."""
    
    for attempt in range(1, max_attempts + 1):
        print(f"\nAttempt {attempt}/{max_attempts} to build a {hops}-hop circuit")
        
        # Generate our custom path
        circuit_path = generate_circuit(hops)
        
        if not circuit_path or len(circuit_path) < hops:
            print(f"Failed to generate a complete {hops}-hop circuit")
            continue
            
        # Format path for circuit creation
        path_fingerprints = [relay.fingerprint for relay in circuit_path]
        
        print(f"Building {hops}-hop circuit:")
        for i, relay in enumerate(circuit_path):
            print(f"Hop {i+1}: {relay.nickname} ({relay.fingerprint}) - {relay.address}:{relay.or_port}")
        
        # Create the circuit with a timeout
        try:
            # Check if relays are likely available by checking published times
            current_time = time.time()
            for i, relay in enumerate(circuit_path):
                if hasattr(relay, 'published') and (current_time - relay.published.timestamp()) > 86400:  # Older than 24h
                    print(f"Warning: Relay {relay.nickname} was published {(current_time - relay.published.timestamp())//3600}h ago")
            
            circuit_id = controller.new_circuit(path_fingerprints, await_build=True, timeout=20)
            print(f"\nCircuit {circuit_id} built successfully!")
            return circuit_id, circuit_path
            
        except Exception as e:
            print(f"Failed to build circuit: {e}")
            # If this was the last attempt, re-raise the exception
            if attempt == max_attempts:
                print("Maximum retry attempts reached. Could not build circuit.")
                return None, None
            
            print("Retrying with different relays...")
            time.sleep(1)  # Wait a bit before retrying
    
    return None, None

def keep_circuit_alive(controller, circuit_id):
    """Keep the circuit alive indefinitely until user interrupts."""
    print("\nCircuit is now ready for use!")
    print("Configure your browser to use SOCKS proxy 127.0.0.1:9050")
    print("The script will keep running and maintain your circuit.")
    print("Press Ctrl+C to close the circuit and exit.")
    
    try:
        while True:
            # Print status every 60 seconds
            for i in range(60):
                time.sleep(1)
            print(f"Circuit {circuit_id} still active...")
    except KeyboardInterrupt:
        print("\nClosing circuit and exiting...")
        if controller.is_alive():
            try:
                controller.close_circuit(circuit_id)
                print(f"Circuit {circuit_id} closed")
            except:
                pass