import sys
import stem.control
from stem.control import Controller
from circuit_builder import build_circuit_with_retry, test_circuit, keep_circuit_alive

def main():
    print("Starting custom Tor circuit creator")
    
    try:
        with Controller.from_port(port=9051) as controller:
            try:
                controller.authenticate()
                print("Successfully connected to Tor control port")
                print(f"Tor version: {controller.get_version()}")
                
                bootstrap_status = controller.get_info("status/bootstrap-phase")
                print(f"Tor bootstrap status: {bootstrap_status}")
                
                if not "PROGRESS=100" in bootstrap_status:
                    print("Tor is not bootstrapped yet.")
            except Exception as e:
                print(f"Error authenticating to Tor control port: {e}")
                print("\nMake sure Tor is running with ControlPort enabled")
                print("Add 'ControlPort 9051' and 'CookieAuthentication 1' to your torrc file")
                return
        
        with Controller.from_port(port=9051) as controller:
            controller.authenticate()
            
            circuit_id, path = build_circuit_with_retry(controller, hops=4, max_attempts=5)
            
            if circuit_id:
                test_result = test_circuit(controller, circuit_id)
                
                if test_result:
                    keep_circuit_alive(controller, circuit_id)
                else:
                    print("Circuit test failed")
                    if controller.is_alive():
                        try:
                            controller.close_circuit(circuit_id)
                            print(f"\nCircuit {circuit_id} closed")
                        except:
                            pass
            else:
                print("\nFailed to create a working circuit after multiple attempts")
            
    except KeyboardInterrupt:
        print("\nExiting due to user interrupt")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()