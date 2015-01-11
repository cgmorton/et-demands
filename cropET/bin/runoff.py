import util

def runoff(foo, foo_day, OUT):
    """ """
    # print 'in runoff()...'
    #Private Sub runoff()
    #Dim Pnet, CN, AWCI, AWCIII, CNIII, CNI, CNII As Double

    #' curve number method for computing runoff
    #' bring in CNII for antecedent condition II
    #' from crop-soil combination
    #' check to insure CNII is within limits

    CNII = foo.CN2
    if CNII < 10:    CNII = 10
    if CNII > 100:    CNII = 100

    #' compute CN's for other antecedent conditions

    CNI = CNII / (2.281 - 0.01281 * CNII) #' Hawkins et al., 1985, ASCE Irr.Drn. 11(4):330-340
    CNIII = CNII / (0.427 + 0.00573 * CNII)

    #' determine antecedent condition
    #' presume that AWCIII is quite moist (when only 1/2 of REW is evaporated)
    #' be sure that REW and TEW are shared

    AWCIII = 0.5 * foo.REW

    #' presume that dry AWCI condition occurs somewhere between REW and TEW

    AWCI = 0.7 * foo.REW + 0.3 * foo.TEW

    #' Value for CN adjusted for soil moisture

    if AWCI <= AWCIII:    AWCI = AWCIII + 0.01 #'make sure AWCI>AWCIII
    if foo.Depl_surface < AWCIII:   
        CN = CNIII
    else:
        if foo.Depl_surface > AWCI:   
            CN = CNI
        else:
            CN = ((foo.Depl_surface - AWCIII) * CNI + (AWCI - foo.Depl_surface) * CNIII) / (AWCI - AWCIII)
    foo.S = 250 * (100 / CN - 1)
    s = 'runoff():a CN %s  Depl_surface %s  AWCIII %s  CNI %s  AWCI %s  CNIII %s\n'
    t = (CN, foo.Depl_surface, AWCIII, CNI, AWCI, CNIII) 
    OUT.debug(s % t)

    #' if irrigations are automatically scheduled, then base runoff on an average of
    #' conditions for prior four days to smooth results.

    OUT.debug('runoff():b SRO %s  irrFlag %s  S %s\n' % (foo.SRO, foo.irrFlag, foo.S))
    if foo.irrFlag:    #' was Irr > 0:   
        Pnet4 = foo_day.Precip - 0.2 * foo.S4 #' initial abstraction
        Pnet3 = foo_day.Precip - 0.2 * foo.S3 #' initial abstraction
        Pnet2 = foo_day.Precip - 0.2 * foo.S2 #' initial abstraction
        Pnet1 = foo_day.Precip - 0.2 * foo.S1 #' initial abstraction
        if Pnet4 < 0:    Pnet4 = 0
        if Pnet3 < 0:    Pnet3 = 0
        if Pnet2 < 0:    Pnet2 = 0
        if Pnet1 < 0:    Pnet1 = 0
        foo.SRO = (Pnet4 * Pnet4 / (foo_day.Precip + 0.8 * foo.S4) + Pnet3 * Pnet3 
               / (foo_day.Precip + 0.8 * foo.S3) + Pnet2 * Pnet2 / 
               (foo_day.Precip + 0.8 * foo.S2) + Pnet1 * Pnet1 / (foo_day.Precip + 0.8 * foo.S1)) / 4

        s = 'runoff():c SRO %s  Pnet4 %s  S4 %s  Pnet3 %s  S3 %s  Pnet2 %s  S2 %s  Pnet1 %s  S1 %s\n'
        t = (foo.SRO, Pnet4, foo.S4, Pnet3, foo.S3, Pnet2, foo.S2, Pnet1, foo.S1)
        OUT.debug(s % t)

        foo.S4 = foo.S3
        foo.S3 = foo.S2
        foo.S2 = foo.S1
        foo.S1 = foo.S
    else:
        #' non-irrigated runoff

        Pnet = foo_day.Precip - 0.2 * foo.S #' initial abstraction
        if Pnet < 0:    
            Pnet = 0
        foo.SRO = Pnet * Pnet / (foo_day.Precip + 0.8 * foo.S)

