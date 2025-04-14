import time
import stem.control
import socks
from consensus import fetch_consensus
from relay_classification import classify_relays
from relay_selection import select_guard, select_middle, select_exit

def generate_circuit(num_hops=4):
    consensus = fetch_consensus()
    if not consensus or len(consensus) == 0:
        print("Failed to fetch consensus data")
        return []
        
    relays = classify_relays(consensus)
    circuit = []
    guard = select_guard(relays)
    if guard:
        circuit.append(guard)
    else:
        print("Failed to select a guard node")
        return []
    
    for i in range(num_hops - 2):
        middle = select_middle(relays, circuit)
        if middle:
            circuit.append(middle)
        else:
            print(f"Failed to select middle node {i+2}")
            return []
    
    exit = select_exit(relays, circuit)
    if exit:
        circuit.append(exit)
    else:
        print("Failed to select an exit node")
        return []
    
    return circuit

def test_circuit(controller, circuit_id):
    if not circuit_id:
        print("No circuit to test")
        return False
    
    try:
        controller.set_conf('__LeaveStreamsUnattached', '1')        
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
        
        controller.add_event_listener(attach_stream, stem.control.EventType.STREAM)
        import socket
        import socks
        s = socks.socksocket()
        s.set_proxy(socks.SOCKS5, "127.0.0.1", 9050)
        
        try:
            print("Connecting to check.torproject.org...")
            s.connect(("check.torproject.org", 80))
            s.send(b"GET / HTTP/1.1\r\nHost: check.torproject.org\r\n\r\n")
            response = s.recv(1024)
            if response:
                s.close()
                print("Connection andd data test successful!")
                return True
            else:
                print("Connection succeeded but received no data")
                s.close()
                return False
                
        except Exception as e:
            print(f"Error testing connection: {e}")
            return False
        finally:
            controller.remove_event_listener(attach_stream)
            controller.reset_conf('__LeaveStreamsUnattached')
            
    except Exception as e:
        print(f"Failed to test circuit: {e}")
        return False

def build_circuit_with_retry(controller, hops=4, max_attempts=10):
    
    for attempt in range(1, max_attempts + 1):
        print(f"\nAttempt {attempt}/{max_attempts} to build a {hops}-hop circuit")
        
        circuit_path = generate_circuit(hops)
        
        if not circuit_path or len(circuit_path) < hops:
            print(f"Failed to generate a complete {hops}-hop circuit")
            continue
            
        path_fingerprints = [relay.fingerprint for relay in circuit_path]
        
        for i, relay in enumerate(circuit_path):
            print(f"Hop {i+1}: {relay.nickname} ({relay.fingerprint}) - {relay.address}:{relay.or_port}")
        
        try:
            circuit_id = controller.new_circuit(path_fingerprints, await_build=True, timeout=20)
            print(f"\nCircuit {circuit_id} built successfully!")
            return circuit_id, circuit_path
            
        except Exception as e:
            print(f"Failed to build circuit: {e}")
            if attempt == max_attempts:
                print("Maximum retry attempts reached. Could not build circuit.")
                return None, None
            
            print("Retrying")
            time.sleep(1) 
    
    return None, None

def keep_circuit_alive(controller, circuit_id):
    print("\nCircuit is now ready for use")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if controller.is_alive():
            try:
                controller.close_circuit(circuit_id)
                print(f"Circuit {circuit_id} closed")
            except:
                pass