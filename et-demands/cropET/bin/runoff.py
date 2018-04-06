import logging

def runoff(foo, foo_day, debug_flag=False):
    """Curve number method for computing runoff."""
    # logging.debug('runoff()')

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

    # Presume that dry AWCI condition occurs somewhere between REW and TEW
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
    if debug_flag:
        logging.debug(
            ('runoff(): CN %.6f  depl_surface %.6f  AWCIII %.6f  ') %
            (cn, foo.depl_surface, AWCIII))
        logging.debug(
            ('runoff(): CNI %.6f  AWCI %.6f  CNIII %.6f') %
            (CNI, AWCI, CNIII))

    # If irrigations are automatically scheduled, base runoff on an average of
    #   conditions for prior four days to smooth results.
    logging.debug('runoff(): SRO %.6f  irr_flag %d  S %.6f' % (
        foo.sro, foo.irr_flag, foo.s))
    if foo.irr_flag:
        # Initial abstraction
        ppt_net4 = max(foo_day.precip - 0.2 * foo.s4, 0)
        ppt_net3 = max(foo_day.precip - 0.2 * foo.s3, 0)
        ppt_net2 = max(foo_day.precip - 0.2 * foo.s2, 0)
        ppt_net1 = max(foo_day.precip - 0.2 * foo.s1, 0)
        foo.sro = 0.25 * (
            ppt_net4 ** 2 / (foo_day.precip + 0.8 * foo.s4) +
            ppt_net3 ** 2 / (foo_day.precip + 0.8 * foo.s3) +
            ppt_net2 ** 2 / (foo_day.precip + 0.8 * foo.s2) +
            ppt_net1 ** 2 / (foo_day.precip + 0.8 * foo.s1))
        if debug_flag:
            logging.debug(
                ('runoff(): Pnet4 %.6f  S4 %.6f  Pnet3 %.6f  S3 %.6f') %
                (ppt_net4, foo.s4, ppt_net3, foo.s3))
            logging.debug(
                ('runoff(): Pnet2 %.6f  S2 %.6f  Pnet1 %.6f  S1 %.6f') %
                (ppt_net2, foo.s2, ppt_net1, foo.s1))
            logging.debug('runoff(): SRO %.6f' % foo.sro)

        foo.s4 = foo.s3
        foo.s3 = foo.s2
        foo.s2 = foo.s1
        foo.s1 = foo.s
    else:
        # Non-irrigated runoff
        # Initial abstraction
        ppt_net = max(foo_day.precip - 0.2 * foo.s, 0)
        foo.sro = ppt_net * ppt_net / (foo_day.precip + 0.8 * foo.s)
