
def classify_relays(consensus):
    guards = []
    middles = []
    exits = []
    
    guard_flag_count = 0
    exit_flag_count = 0
    both_flags_count = 0
    
    for relay in consensus:
        
        is_guard = False
        is_exit = False
        
        if hasattr(relay, 'flags'):
            if 'Guard' in relay.flags:
                guard_flag_count += 1
                is_guard = True
            
            if 'Exit' in relay.flags:
                exit_flag_count += 1
                is_exit = True
        
        if not is_exit and hasattr(relay, 'exit_policy') and relay.exit_policy is not None:
            try:
                can_exit = relay.exit_policy.is_exiting_allowed()
                if can_exit:
                    exit_flag_count += 1
                    is_exit = True
            except Exception as e:
                pass
        
        if is_guard and is_exit:
            both_flags_count += 1
            guards.append(relay) 
            exits.append(relay)
        elif is_guard:
            guards.append(relay)
        elif is_exit:
            exits.append(relay)
        else:
            middles.append(relay)
    
    print(f"\nClassified relays - Guards: {len(guards)}, Middles: {len(middles)}, Exits: {len(exits)}")
    
    # If no guards were found but we have relays, use some middle relays as guards    
    if len(guards) == 0 and len(middles) > 0:
        print("No guards found! Using fastest middle relays as guards.")
        sorted_middles = sorted(middles, key=lambda r: getattr(r, 'bandwidth', 0), reverse=True)
        guards = sorted_middles[:max(len(sorted_middles) // 10, 5)]
    
    # If no exits were found but we have relays, use some middle relays as exits
    if len(exits) == 0 and len(middles) > 0:
        print("No exits found! Using fastest middle relays as exits.")
        sorted_middles = sorted(middles, key=lambda r: getattr(r, 'bandwidth', 0), reverse=True)
        exits = sorted_middles[:max(len(sorted_middles) // 10, 5)]
    
    return {
        'guards': guards,
        'middles': middles,
        'exits': exits,
        'all': consensus
    }