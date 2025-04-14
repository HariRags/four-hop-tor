# relay_selection.py - Functions for selecting relays for circuits
import random

def select_relay_weighted(relays):
    """Select a relay weighted by bandwidth."""
    if not relays:
        return None
        
    try:
        total_bandwidth = sum(relay.bandwidth for relay in relays)
        pick = random.uniform(0, total_bandwidth)
        
        running_sum = 0
        for relay in relays:
            running_sum += relay.bandwidth
            if pick <= running_sum:
                return relay
    except Exception as e:
        print(f"Error in bandwidth weighting: {e}")
        pass
    
    # Fallback to random selection
    return random.choice(relays) if relays else None

def is_same_family(relay1, relay2):
    """Check if two relays are in the same family."""
    try:
        if hasattr(relay1, 'family') and hasattr(relay2, 'family'):
            return (relay1.fingerprint in relay2.family) or (relay2.fingerprint in relay1.family)
    except:
        pass
    return False

def is_same_subnet(relay1, relay2):
    """Check if two relays are in the same /16 subnet."""
    try:
        if hasattr(relay1, 'address') and hasattr(relay2, 'address'):
            # Get the first two octets of the IP address
            subnet1 = '.'.join(relay1.address.split('.')[:2])
            subnet2 = '.'.join(relay2.address.split('.')[:2])
            return subnet1 == subnet2
    except:
        pass
    return False

def select_guard(relays):
    """Select a guard node."""
    guard_relays = [r for r in relays['guards'] if 'Fast' in r.flags and 'Stable' in r.flags]
    if not guard_relays:
        # Fallback to any guard relay
        guard_relays = relays['guards']
        if not guard_relays:
            print("No suitable guard relays found!")
            return None
    return select_relay_weighted(guard_relays)

def select_middle(relays, previous_relays):
    """Select a middle node that's not in the same family or /16 subnet as any previous relay."""
    # Filter out relays in the same family or subnet
    suitable_relays = []
    
    # Middle position can use both middle and guard relays (but not ones already in circuit)
    candidates = relays['middles'] + relays['guards']
    
    for relay in candidates:
        # Skip if it's already in our path
        if relay in previous_relays:
            continue
        
        # Skip if it's in the same family as any previous relay
        if any(is_same_family(relay, prev) for prev in previous_relays):
            continue
        
        # Skip if it's in the same /16 subnet as any previous relay
        if any(is_same_subnet(relay, prev) for prev in previous_relays):
            continue
            
        suitable_relays.append(relay)
    
    if not suitable_relays:
        print(f"No suitable middle relays found for position {len(previous_relays) + 1}!")
        # Fallback to any relay not in the circuit
        suitable_relays = [r for r in candidates if r not in previous_relays]
        if not suitable_relays:
            return None
    
    return select_relay_weighted(suitable_relays)

def select_exit(relays, previous_relays):
    """Select an exit node."""
    # Filter suitable exit relays
    suitable_exits = []
    for relay in relays['exits']:
        # Skip if it's already in our path
        if relay in previous_relays:
            continue
        
        # Skip if it's in the same family as any previous relay
        if any(is_same_family(relay, prev) for prev in previous_relays):
            continue
        
        # Skip if it's in the same /16 subnet as any previous relay
        if any(is_same_subnet(relay, prev) for prev in previous_relays):
            continue
            
        suitable_exits.append(relay)
    
    if not suitable_exits:
        print("No suitable exit relays found!")
        # Fallback to any exit relay not in the circuit
        suitable_exits = [r for r in relays['exits'] if r not in previous_relays]
        if not suitable_exits:
            return None
    
    return select_relay_weighted(suitable_exits)