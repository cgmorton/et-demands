def runoff(foo, foo_day, OUT):
    """curve number method for computing runoff."""
    # print 'in runoff()...'

    # Bring in CNII for antecedent condition II from crop-soil combination
    # Check to insure CNII is within limits
    CNII = foo.cn2
    if CNII < 10:
        CNII = 10
    if CNII > 100:
        CNII = 100

    # Compute CN's for other antecedent conditions
    CNI = CNII / (2.281 - 0.01281 * CNII) #' Hawkins et al., 1985, ASCE Irr.Drn. 11(4):330-340
    CNIII = CNII / (0.427 + 0.00573 * CNII)

    # Determine antecedent condition
    # Presume that AWCIII is quite moist (when only 1/2 of REW is evaporated)
    # Be sure that REW and TEW are shared
    AWCIII = 0.5 * foo.rew

    #' presume that dry AWCI condition occurs somewhere between REW and TEW
    AWCI = 0.7 * foo.rew + 0.3 * foo.tew

    # Value for CN adjusted for soil moisture
    # Make sure AWCI>AWCIII
    if AWCI <= AWCIII:
        AWCI = AWCIII + 0.01 
    if foo.depl_surface < AWCIII:   
        CN = CNIII
    else:
        if foo.depl_surface > AWCI:   
            CN = CNI
        else:
            CN = ((foo.depl_surface - AWCIII) * CNI + (AWCI - foo.depl_surface) * CNIII) / (AWCI - AWCIII)
    foo.S = 250 * (100 / CN - 1)
    s = 'runoff():a CN %s  Depl_surface %s  AWCIII %s  CNI %s  AWCI %s  CNIII %s\n'
    t = (CN, foo.depl_surface, AWCIII, CNI, AWCI, CNIII) 
    OUT.debug(s % t)

    # If irrigations are automatically scheduled, base runoff on an average of
    #   conditions for prior four days to smooth results.

    OUT.debug('runoff():b SRO %s  irr_flag %s  S %s\n' % (
        foo.SRO, foo.irr_flag, foo.S))
    # was Irr > 0:
    if foo.irr_flag:    
        # Initial abstraction
        Pnet4 = foo_day.precip - 0.2 * foo.S4
        Pnet3 = foo_day.precip - 0.2 * foo.S3
        Pnet2 = foo_day.precip - 0.2 * foo.S2
        Pnet1 = foo_day.precip - 0.2 * foo.S1 
        if Pnet4 < 0:
            Pnet4 = 0
        if Pnet3 < 0:
            Pnet3 = 0
        if Pnet2 < 0:
            Pnet2 = 0
        if Pnet1 < 0:
            Pnet1 = 0
        foo.SRO = (
            Pnet4 * Pnet4 / (foo_day.precip + 0.8 * foo.S4) + Pnet3 * Pnet3 
               / (foo_day.precip + 0.8 * foo.S3) + Pnet2 * Pnet2 / 
               (foo_day.precip + 0.8 * foo.S2) + Pnet1 * Pnet1 / (foo_day.precip + 0.8 * foo.S1)) / 4
        s = 'runoff():c SRO %s  Pnet4 %s  S4 %s  Pnet3 %s  S3 %s  Pnet2 %s  S2 %s  Pnet1 %s  S1 %s\n'
        t = (foo.SRO, Pnet4, foo.S4, Pnet3, foo.S3, Pnet2, foo.S2, Pnet1, foo.S1)
        OUT.debug(s % t)

        foo.S4 = foo.S3
        foo.S3 = foo.S2
        foo.S2 = foo.S1
        foo.S1 = foo.S
    else:
        # Non-irrigated runoff
        # Initial abstraction
        Pnet = foo_day.precip - 0.2 * foo.S 
        if Pnet < 0:    
            Pnet = 0
        foo.SRO = Pnet * Pnet / (foo_day.precip + 0.8 * foo.S)
