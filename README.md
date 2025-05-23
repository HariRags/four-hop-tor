# Tor Custom Circuit Creation System
## Overview
This project implements a custom Tor circuit creation system that builds and maintains 4-hop circuits through the Tor network. It implements Tor's relay selection algorithm with bandwidth-weighted selection and constructs circuits that follow Tor's security principles.
The commands needed for setup and running the script are present in the report.

## Relay Selection Algorithm
I have tried to emulate Tor's relay selection alogrithm as much as possible. The relays are selected pseudo randomly based on the following parameters and methods (explained in even more detail in the script explanation for `relay_selction.py`)
- No 2 relays in  the circuit will have the same `family` (Checked using each relay's fingerprint and matching it to the otehr relay's `family` list)
- No 2 relays shall be used twice (i.e all relays will be distinct)
- No 2 relays will be in the same /16 subnet
- First node is a guard node (has the `guard` attribute)
- We prioritise choosing guard nodes which are `Fast` and `Stable` (however this is not necessary)
- The relay selection is also weighted by bandwidth and tries to emulate tor's algorithm as much as possible as detailed in `node_select.c` , functions  - `smartlist_choose_node_by_bandwidth_weights(const smartlist_t *sl,bandwidth_weight_rule_t rule)`, `choose_array_element_by_weight(const uint64_t *entries, int n_entries)`; (tor's algo has additional complications for guard and exit as well, however I have applied the same algo for all relays regardless of exit or guard), the algo is as follows
    - Sums up the bandwidth of all the relays in the list
    - Selects a random value between 0 and and total bandwidth 
    - Iterate over the relays while summing up the bandwidth, when the cumulative sum exceeds the randomly chosen value, select that relay 

## Nyx
`sudo apt install nyx`
`sudo nyx`
This runs nyx, then navigate to the connections panel in menu to verify that the circuit has been built(after running the script)

## Streams
To ennsure that all new connections will go through our Tor circuit and not some other Tor circuit, we disable Tor's default behavior of automatically attaching streams to circuits. Then we use a stream listener to ensure that all new strams will be attached to our circuit.
As we keep the circuit alive indefinitely, multiple streams can use our 1 circuit.

## Script Explanation

### File: `consensus.py`
1. **Connect to the Tor Control Port**:
   - The function connects to the Tor control port (default: `9051`) using the Stem library's `Controller`.

2. **Authenticate**:
   - It authenticates with the Tor daemon using the default authentication method( Cookies in this case)

3. **Retrieve Consensus**:
   - The function calls `controller.get_network_statuses()` to fetch the list of all relays in the Tor network.

4. **Return Consensus**:
   - If the consensus is successfully retrieved, it returns a list of relays.
   - If the consensus is empty or an error occurs, it prints an error message and returns an empty list.

### File: `circuit_builder.py`

This file contains the core logic for building, testing, and maintaining the 4-hop Tor circuit.=

### 1. `generate_circuit(num_hops=4)`

 Generates a custom Tor circuit with the specified number of hops (default: 4).

1. Fetches the Tor network consensus using `fetch_consensus()`.
2. Classifies relays into guards, middles, and exits using `classify_relays()`.
3. Selects:
   - A **Guard** relay for the first hop using `select_guard()`.
   - **Middle** relays for intermediate hops using `select_middle()`.
   - An **Exit** relay for the final hop using `select_exit()`.
4. Returns the list of relays forming the circuit.

### 2. `test_circuit(controller, circuit_id)`

 Tests the functionality of a created circuit by making a connection through it.

1. Configures Tor to leave streams unattached (`__LeaveStreamsUnattached`).
2. Sets up a stream listener to attach new streams to the specified circuit.
3. Makes a connection to `check.torproject.org` through the SOCKS proxy (`127.0.0.1:9050`).
4. Verifies the connection and checks if data is received.

### 3. `build_circuit_with_retry(controller, hops=4, max_attempts=10)`

Attempts to build a custom circuit with retries in case of failure.

1. Tries to generate a circuit using `generate_circuit()`.
2. Builds the circuit using `controller.new_circuit()` with the selected relays.
3. Retries up to `max_attempts` times if circuit creation fails.
4. Returns the circuit ID and the path if successful.

### 4. `keep_circuit_alive(controller, circuit_id)`

Keeps the custom circuit alive and routes all new streams through it.

1. Configures Tor to leave streams unattached (`__LeaveStreamsUnattached`).
2. Sets up a stream listener to attach new streams to the specified circuit.
3. Keeps the circuit alive indefinitely until the user interrupts (Ctrl+C).
4. Cleans up by removing the event listener and closing the circuit.

### File: `relay_classification.py`

This file contains the logic for classifying relays from the Tor network consensus into categories: guards, middles, and exits.

 Classifies relays from the consensus into guards, middles, and exits based on their flags and capabilities.

### File: `relay_selection.py`

### 1. `select_relay_weighted(relays)`

1. **Initialize Categories**:
   - Creates empty lists for `guards`, `middles`, and `exits`.

2. **Iterate Through Relays**:
   - For each relay in the consensus:
     - Checks if the relay has the `Guard` flag.
     - Checks if the relay has the `Exit` flag or a permissive exit policy.
     - Adds the relay to the appropriate category:
       - **Guard**: If it has the `Guard` flag.
       - **Exit**: If it has the `Exit` flag or allows exiting.
       - **Middle**: If it doesn't qualify as a guard or exit.

3. **Handle Edge Cases**:
   - If no guards are found, selects the fastest middle relays to act as guards.
   - If no exits are found, selects the fastest middle relays to act as exits.

4. **Return Results**:
   - Returns a dictionary containing the classified relays:
     - `guards`: List of guard relays.
     - `middles`: List of middle relays.
     - `exits`: List of exit relays.
     - `all`: The original consensus.

### 2. `is_same_family(relay1, relay2)`
Checks if two relays belong to the same family
1. Compares the family attribute of both relays.
2. Returns True if either relay's fingerprint is in the other's family list.

### 3. `is_same_subnet(relay1, relay2)`
Checks if two relays are in the same /16 subnet
1. Extracts the first two octets of the IP addresses of both relays.
2. Returns True if the subnets match.

### 4. `select_guard(relays)`
Selects a guard relay for the first hop of the circuit.
1. Filters relays with the Guard flag and Fast and Stable flags.
2. If no suitable guards are found, falls back to any guard relay.
3. Uses select_relay_weighted to select a guard relay.

### 5. `select_middle(relays, previous_relays)`
Selects a middle relay for intermediate hops in the circuit.
1. Combines middle relays and unused guard relays as candidates.
2. Filters out relays that:
    - Are already in the circuit.
    - Belong to the same family as any relay in the circuit.
    - Are in the same subnet as any relay in the circuit.
3. Uses select_relay_weighted to select a middle relay.
4. If no suitable relays are found, selects any unused relay.

### 6. `select_exit(relays, previous_relays)`
Selects an exit relay for the final hop of the circuit.
1. Filters exit relays that:
    - Are not already in the circuit.
    - Do not belong to the same family as any relay in the circuit.
    - Are not in the same subnet as any relay in the circuit.
2. Uses select_relay_weighted to select an exit relay.
3. If no suitable exits are found, selects any unused exit relay.