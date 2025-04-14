# main.py - Main program entry point
import sys
import stem.control
from stem.control import Controller
from circuit_builder import build_circuit_with_retry, test_circuit, keep_circuit_alive

def main():
    """Main function to create and test a custom Tor circuit."""
    print("Starting custom Tor circuit creator...")
    
    try:
        # Verify Tor is properly configured
        with Controller.from_port(port=9051) as controller:
            try:
                controller.authenticate()
                print("Successfully connected to Tor control port")
                print(f"Tor version: {controller.get_version()}")
                
                # Check if Tor is properly bootstrapped
                bootstrap_status = controller.get_info("status/bootstrap-phase")
                print(f"Tor bootstrap status: {bootstrap_status}")
                
                if not "PROGRESS=100" in bootstrap_status:
                    print("Warning: Tor is not fully bootstrapped, which may affect consensus download")
            except Exception as e:
                print(f"Error authenticating to Tor control port: {e}")
                print("\nMake sure Tor is running with ControlPort enabled")
                print("Add 'ControlPort 9051' and 'CookieAuthentication 1' to your torrc file")
                return
        
        # Use a new controller for circuit building
        with Controller.from_port(port=9051) as controller:
            controller.authenticate()
            
            # Build custom circuit with retry
            circuit_id, path = build_circuit_with_retry(controller, hops=4, max_attempts=5)
            
            if circuit_id:
                # Test the circuit
                test_result = test_circuit(controller, circuit_id)
                
                if test_result:
                    print("\n" + "="*60)
                    print("CIRCUIT READY FOR BROWSING")
                    print("="*60)
                    print("To use this circuit:")
                    print("1. Configure your browser to use SOCKS proxy:")
                    print("   • Address: 127.0.0.1")
                    print("   • Port: 9050") 
                    print("   • Type: SOCKS5")
                    print("   • Enable 'Proxy DNS when using SOCKS v5' if available")
                    print("2. Keep this terminal window open")
                    print("="*60)
                    
                    # Keep circuit alive indefinitely until user exits
                    keep_circuit_alive(controller, circuit_id)
                else:
                    print("Circuit test failed, not keeping circuit open")
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