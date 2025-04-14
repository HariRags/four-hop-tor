# relay_classification.py - Functions to classify and select relays

def classify_relays(consensus):
    """Classify relays as guards, middles, and exits with improved detection."""
    guards = []
    middles = []
    exits = []
    
    # Debug counters
    guard_flag_count = 0
    exit_flag_count = 0
    both_flags_count = 0
    
    for relay in consensus:
        # Debug: print first few relays to understand structure
        if len(guards) == 0 and len(exits) == 0 and len(middles) < 3:
            print(f"\nDEBUG: Sample relay: {relay.nickname}")
            print(f"  Fingerprint: {relay.fingerprint}")
            print(f"  Flags: {relay.flags if hasattr(relay, 'flags') else 'No flags attribute'}")
            print(f"  Raw flags: {getattr(relay, '_flags', 'No _flags attribute')}")
            if hasattr(relay, 'exit_policy'):
                print(f"  Exit policy exists: {'Yes, and is not None' if relay.exit_policy is not None else 'Yes, but is None'}")
                if relay.exit_policy is not None:
                    try:
                        print(f"  Exit policy allows: {relay.exit_policy.is_exiting_allowed()}")
                    except Exception as e:
                        print(f"  Error checking exit policy: {e}")
            else:
                print(f"  Exit policy exists: No")
        
        is_guard = False
        is_exit = False
        
        # Check for Guard flag
        if hasattr(relay, 'flags'):
            if 'Guard' in relay.flags:
                guard_flag_count += 1
                is_guard = True
            
            # Also check for Exit flag
            if 'Exit' in relay.flags:
                exit_flag_count += 1
                is_exit = True
        
        # Check for exit capabilities from exit_policy if not already determined from flags
        if not is_exit and hasattr(relay, 'exit_policy') and relay.exit_policy is not None:
            try:
                can_exit = relay.exit_policy.is_exiting_allowed()
                if can_exit:
                    exit_flag_count += 1
                    is_exit = True
            except Exception as e:
                # Silently ignore exit_policy errors
                pass
        
        # Classify based on flags
        if is_guard and is_exit:
            both_flags_count += 1
            guards.append(relay)  # Add as both
            exits.append(relay)
        elif is_guard:
            guards.append(relay)
        elif is_exit:
            exits.append(relay)
        else:
            middles.append(relay)
    
    print(f"\nFlag detection stats:")
    print(f"  Relays with Guard flag: {guard_flag_count}")
    print(f"  Relays with Exit capability: {exit_flag_count}")
    print(f"  Relays with both Guard+Exit: {both_flags_count}")
    
    print(f"\nClassified relays - Guards: {len(guards)}, Middles: {len(middles)}, Exits: {len(exits)}")
    
    # If no guards were found but we have relays, use some middle relays as guards
    if len(guards) == 0 and len(middles) > 0:
        print("No guards found! Using fastest middle relays as guards.")
        # Sort middle relays by bandwidth and use top 10% as guards
        sorted_middles = sorted(middles, key=lambda r: getattr(r, 'bandwidth', 0), reverse=True)
        guards = sorted_middles[:max(len(sorted_middles) // 10, 5)]
        print(f"Selected {len(guards)} middle relays to act as guards")
    
    # If no exits were found but we have relays, use some middle relays as exits
    if len(exits) == 0 and len(middles) > 0:
        print("No exits found! Using fastest middle relays as exits.")
        # Sort middle relays by bandwidth and use top 10% as exits
        sorted_middles = sorted(middles, key=lambda r: getattr(r, 'bandwidth', 0), reverse=True)
        exits = sorted_middles[:max(len(sorted_middles) // 10, 5)]
        print(f"Selected {len(exits)} middle relays to act as exits")
    
    return {
        'guards': guards,
        'middles': middles,
        'exits': exits,
        'all': consensus
    }