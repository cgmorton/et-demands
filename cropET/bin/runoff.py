def runoff(foo, foo_day, OUT):
    """Curve number method for computing runoff."""
    # print 'in runoff()...'

    # Bring in CNII for antecedent condition II from crop-soil combination
    # Check to insure CNII is within limits
    CNII = min(max(foo.cn2, 10), 100)

    # Compute CN's for other antecedent conditions
    # Hawkins et al., 1985, ASCE Irr.Drn. 11(4):330-340
    CNI = CNII / (2.281 - 0.01281 * CNII) 
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
        cn = CNIII
    else:
        if foo.depl_surface > AWCI:   
            cn = CNI
        else:
            cn = (
                ((foo.depl_surface - AWCIII) * CNI +
                 (AWCI - foo.depl_surface) * CNIII) / (AWCI - AWCIII))
    foo.s = 250 * (100 / cn - 1)
    s = 'runoff():a cn %s  depl_surface %s  AWCIII %s  CNI %s  AWCI %s  CNIII %s\n'
    t = (cn, foo.depl_surface, AWCIII, CNI, AWCI, CNIII) 
    OUT.debug(s % t)

    # If irrigations are automatically scheduled, base runoff on an average of
    #   conditions for prior four days to smooth results.
    OUT.debug('runoff():b SRO %s  irr_flag %s  S %s\n' % (
        foo.SRO, foo.irr_flag, foo.s))
    if foo.irr_flag:    
        # Initial abstraction
        ppt_net4 = max(foo_day.precip - 0.2 * foo.S4, 0)
        ppt_net3 = max(foo_day.precip - 0.2 * foo.S3, 0)
        ppt_net2 = max(foo_day.precip - 0.2 * foo.S2, 0)
        ppt_net1 = max(foo_day.precip - 0.2 * foo.S1 , 0)
        foo.SRO = 0.25 * (
            ppt_net4 ** 2 / (foo_day.precip + 0.8 * foo.S4) +
            ppt_net3 ** 2 / (foo_day.precip + 0.8 * foo.S3) +
            ppt_net2 ** 2 / (foo_day.precip + 0.8 * foo.S2) +
            ppt_net1 ** 2 / (foo_day.precip + 0.8 * foo.S1))
        s = ('runoff():c SRO %s  Pnet4 %s  S4 %s  Pnet3 %s  S3 %s  '+
             'Pnet2 %s  S2 %s  Pnet1 %s  S1 %s\n')
        t = (foo.SRO, ppt_net4, foo.S4, ppt_net3, foo.S3,
             ppt_net2, foo.S2, ppt_net1, foo.S1)
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
