import math

PI = math.pi

class refET:

    def __init__(self):
        """ """
        # these were defined as 'static' variable within a Function in the VB.net version 
        self._Tp3 = 0.0 # static
        self._Tp2 = 0.0 # static
        self._Tp1 = 0.0 # static
        self._ndays = 0 # static
        self._lastDay = 0 # static
        self._Rn = 0.0  # static ## not explicity initialized in VB.net code, default is 0 from web search

    #' compute reference ET by all methods and return specified method

    '''
    Public Function ComputeRefET(ByVal yr As Short, ByVal mo As Short, ByVal da As Short, ByVal doy As Short, _
                                 ByVal timeStep As Short, ByVal sdays As Long, ByVal TMax As Single, ByVal TMin As Single, _
                                 ByVal TMean As Single, ByVal TDew As Single, ByVal u24 As Double, ByRef u242 As Double, _
                                 ByVal elevm As Double, ByVal latitude As Double, ByVal sr As Single, _
                                 ByRef Rs As Double, ByVal avgTMax As Single, ByVal avgTMin As Single, _
                                 ByVal Resett As Short, ByRef Harg As Double, ByRef Penman As Double, _
                                 ByRef PreTay As Double, ByRef KimbPeng As Double, ByRef ASCEPMstdr As Double, _
                                 ByRef ASCEPMstdo As Double, ByRef FAO56PM As Double, ByRef KimbPen As Double) As Double

    # pmdata/ETo/Node1E2.dat provides:
        Lat:  48.97 Long: -113.05 Elev  3558 ft
        mo  da  Yr  DoY   TMax   TMin  -> EstRs, EsWind, EsTDew, ASCEr
        TMean  TDew  u24, sr

    '''

    def ComputeRefET(self, yr, mo, da, doy, 
                     timeStep, sdays, TMax, TMin,
                     TMean, TDew, u24, 
                     elevm, latitude, sr,
                     avgTMax, avgTMin, 
                     Resett): 
        """ """

    #        ' compute latent heat of vaporization

        Heatlt = self.aFNHarrison(TMean)

        #    ' compute extraterrestial radiation

        Ra = self.ExtraterrestrialRadiation(doy, latitude)
        #print 'Ra, doy, lat:', Ra, doy, latitude
        #Rso = 0.0!  # force single precision  TODO, make sure that using double precision does not negatively impart results
        Rso = 0.0

        #   ' compute Hargreaves Samani reference ET
        Harg = self.HargreavesSamani(TMax, TMin, TMean, Heatlt, Ra)

        Delta = self.aFNDelta(TMean) #' kPa/C
        ed = self.aFNEs(TDew)

        pressure = self.aFNPressure(elevm)
        Gamma = self.aFNGamma(pressure, Heatlt) #' kPa/C

        #' Estimate clear sky radiation (Rso)
        Rso = self.EstimateClearSkyRadiation(Ra, pressure, ed, latitude, doy)
        if sr < 0.0:
            #' estimate incident solar radiation
            Rs = self.EstimateIncidentRadiation(Rso, TMax, TMin, avgTMax, avgTMin)
        else:
            #' use measured solar radiation
            Rs = sr

        #' compute net radiation

        # Rn82 was passed byRef
        Rn56, Rn82 = self.FAO56NetRadiation(elevm, latitude, doy, Ra, Rs, Rso, TMax, TMin, ed)

        # ' If Ref <= 0.5 Then ht = GrassHt Else ht = AlfHt 'm

        AlfHt = 0.5 #' m
        GrassHt = 0.12 #' m
        htr = AlfHt
        ht = GrassHt #' assume default is grass

        #' Assuming weather measurement surface is that of reference

        Sitehto = ht
        Sitehtr = htr

        #' set anemometer height

        anemom = 2 #' m

        #' Theorectical adjustment (Allen) over grass is:
        #' d = .67 * GrassHt  'SiteHt 'modified 12/21/99 to reflect wind required over grass in std eqns.
        #' zom = .123 * GrassHt  'SiteHt

        #' U242 = U24 * Log((2 - d) / zom) / Log((anemom - 0.67 * Sitehto) / (0.123 * Sitehto))
        #' for Consuse comp, all wind is at 2 m:

        u242 = u24
        U242r = u24

        #' 1982 Kimberly Penman

        #   Call ComputeSoilHeat(Resett, da, timeStep, TMean, Rn56, G82, G82o, GFAO, GFAOr) ' modified 6/24/99
        G82, G82o, GFAO, GFAOr = self.ComputeSoilHeat(Resett, da, timeStep, TMean, Rn56) #' modified 6/24/99

        G = G82
        ## appears to me that this does nothing & variable never actually gets changed to '2', since it is passed byVal
        ## so parts of the ComputeSoilHeat() code will not ever get exercised...
        ## ???????????  TODO check into this during validation work
        #Resett = 2 #' reset variables in ComputeSoilHeat sub first time only

        ea = (self.aFNEs(TMax) + self.aFNEs(TMin)) * 0.5

        penman_results = self.Penmans(latitude, doy, pressure, Rn56, Rn82, ed, ea, Heatlt, Delta, Gamma, TMean, G82, G82o, GFAO, GFAOr, u242)
        Penman, PreTay, KimbPeng, ASCEPMstdr, ASCEPMstdo, FAO56PM, KimbPen = penman_results
        return penman_results, Harg, Rs


    ################################################################################ 
    ### supporting functions ###

    def aFNHarrison(self, T):
        """ """
        #aFNHarrison = 2500000.0! - 2360 * T  # '!' forces single precision, numpy Float32 is option if needed                              
        a = 2500000.0 - 2360 * T  #' J/Kg   Latent Heat of Vaporization
        return a
        

    #' compute extraterresttrial radiaton in MG/M2/day
    def ExtraterrestrialRadiation(self, DoY, lat):
        """ """
        #Dim etr, omega, Dr, latRad, decl As Double
        #' Do not shift this algorithm for southern latitude. Correct as is.
        Gsc = 0.08202 #' MJ/m2/min


        # [131113] Note:  most of constants below were forced to single precision in VB code
        latRad = lat * PI / 180.0  #' Lat is station latitude in degrees
        decl = 0.4093 * math.sin(2.0 * PI * (284.0 + DoY) / 365.0)
        omega = 0.5 * PI - math.atan((-math.tan(latRad) * math.tan(decl)) / 
                (1.0 - math.tan(decl) * math.tan(decl) * math.tan(latRad) * math.tan(latRad)) ** 0.5)
        Dr = 1.0 + 0.033 * math.cos(2.0 * PI * DoY / 365.0)
        etr = (24.0 * 60.0 / PI) * Gsc * Dr * (omega * math.sin(latRad) * math.sin(decl) + 
                math.cos(latRad) * math.cos(decl) * math.sin(omega))
        return etr


    def aFNDelta(self, T):
        """ Eq. 4 + Eq. 7"""
        a = 4098 * self.aFNEs(T) / (T + 237.3) / (T + 237.3) #' kPa/C
        return a

    def aFNEs(self, T):
        """ Eq. 7 """
        a = 0.6108 * math.exp((17.27 * T) / (T + 237.3)) #' Tetens (1930) equation based
        return a

    def aFNPressure(self, elevm):
        """ Eq. 3 """
        #' aFNPressure = 101.3 * ((288 - 0.0065 * elevm) / 288) ^ (9.8 / (0.0065 * 286.9)) ' kPa used by Allen in Idaho
        a = 101.3 * ((293. - 0.0065 * elevm) / 293.) ** (9.8 / (0.0065 * 286.9)) #' kPa ' standardized by ASCE 2005
        return a

    def aFNGamma(self, P, Heatlt):
        """ Eq. ? """
        a = 1013 * P / 0.622 / Heatlt #' kPa/C  cp=1013 J/Kg/C
        return a


    #' estimate clear sky radiation (Rso) using Appendix D method of ASCE-EWRI (2005)
    def EstimateClearSkyRadiation(self, extRa, pressure, ed, latDeg, doy):
        """ Eq. ? """
        waterInAtm = 0.14 * ed * pressure + 2.1 #' mm as of 9/2000 (was cm)
        latRad = latDeg * PI / 180
        kturb = 1.0
        sinphi24 = math.sin(0.85 + 0.3 * latRad * math.sin(2 * PI / 365 * doy - 1.39) - 0.42 * latRad * latRad)
        kbeam = 0.98 * math.exp((-0.00146 * pressure) / (kturb * sinphi24) - 0.075 * (waterInAtm / sinphi24) ** 0.4) #' modified 9/25/2000
        if kbeam < 0.15:
            kdiffuse = 0.18 + 0.82 * kbeam
        else:
            kdiffuse = 0.35 - 0.36 * kbeam
        csRSo = (kbeam + kdiffuse) * extRa
        #print '\n\nEstimateClearSkyRadiation(%s,%s,%s,%s,%s) = %s' %  (extRa, pressure, ed, latDeg, doy, csRSo)
        return csRSo


    #' Estimate incident radiation
    def EstimateIncidentRadiation(self, csRSo, maxT, minT, monMaxT, monMinT):
        """ Eq. 14  """

        dt = maxT - minT          #' temp difference in C
        dtMon = monMaxT - monMinT #' long term monthly temp difference in C
        dt = max(0.1, dt)
        dtMon = max(0.1, dtMon)

        #' Orginally used UI determined function for coefficient B based on arid stations in T-R paper
        #' BTR = 0.023 + 0.1 * System.Math.Exp(-0.2 * dtMon)
        #' Changed to use user specified values 11/21/2012.
        #' Changed input of third Thorton and Running coefficient to include sign 08/22/2013.

        # [131113] got these from modPM.vb, ???
        #TR_b0 = 0.023
        #TR_b1 = 0.1
        #TR_b2 = -0.2
        # [140116] from Alan Harrison
        #TR_b0 = 0.02027573
        #TR_b1 = 0.2110873   
        #TR_b2 = -0.236323278
        # [140123] from open water work for Klamath & in PMControl tab of KLPenmanMonteithManager.xlsm
        ## alan had sent me the wrong coefficients !!!
        TR_b0 = 0.030707571
        TR_b1 = 0.196041874
        TR_b2 = -0.24545929

        BTR = TR_b0 + TR_b1 * math.exp(TR_b2 * dtMon)

        #' estimate daily Rs using Thornton and Running method (added Nov. 1, 2006)
        #incRs = csRSo * (1 - 0.9 * math.exp(-BTR * dt ** 1.5))
        # from Eq. 14
        incRs = csRSo * (1 - 0.9 * math.exp(-BTR * dt ** 1.5))
        #print '\nEstimateIncidentRadiation(%s,%s,%s,%s,%s) = %s' %  (csRSo, maxT, minT, monMaxT, monMinT, incRs)
        #print
        return incRs



    #' FAO 56 Net Radiation
    def FAO56NetRadiation(self, elevation, lat, doy, etRa, incRs, csRSo, maxT, minT, ed):
        """ """
        # ByRef Rn82 As Double
        j = doy
        if lat < 0:
            j = doy - 182
            if j < 1:
                j = j + 365
        Rna1 = 0.26 + 0.1 * math.exp(-(0.0154 * (j - 180)) ** 2)
        Rso75 = 0.75 * etRa
        Rso56 = (0.75 + 0.00002 * elevation) * etRa #' 4/6/94
        if csRSo > 0:
            RsRso = incRs / csRSo #' 24-hours
        else:
            RsRso = 0.7
        if Rso56:
            RsRso56 = incRs / Rso56 #' 24-hours
        else:
            RsRso56 = 0.7
        RsRso = max(0.2, min(RsRso, 1.0))
        RsRso56 = max(0.2, min(RsRso56, 1.0))
        RsRso2use = RsRso #' useRso based on sun angle and water vapor as of 9/25/2000
        if RsRso2use > 0.7:
            Rna = 1.126
            Rnb = -0.07
        else:
            Rna = 1.017
            Rnb = -0.06
        Rbo = 0.000000004903 * 0.5 * ((maxT + 273.16) ** 4 + (minT + 273.16) ** 4) * (Rna1 - 0.139 * math.sqrt(ed))
        Rb = (Rna * RsRso2use + Rnb) * Rbo
        alpha = 0.29 + 0.06 * math.sin((j + 96) / 57.3)
        Rn82 = (1 - alpha) * incRs - Rb

        #' FAO 56 Net Radiation computation

        Rbo56 = 0.000000004903 * 0.5 * ((maxT + 273.16) ** 4 + (minT + 273.16) ** 4) * (0.34 - 0.14 * math.sqrt(ed))
        Rnl56 = (1.35 * RsRso2use - 0.35) * Rbo56
        FAO56NR = (1 - 0.23) * incRs - Rnl56
        return FAO56NR, Rn82



    #' soil heat flux
    #def ComputeSoilHeat(self, Resett, da, timestep, TMean, Rn56, G82, G82o, GFAO, GFAOr): #' modified 6/24/99
    def ComputeSoilHeat(self, Resett, da, timestep, TMean, Rn56): #' modified 6/24/99
        # ByRef G82 As Double, ByRef G82o As Double, ByRef GFAO As Double, ByRef GFAOr As Double
        #Static Rn, Tp3, Tp1, Tp2 As Double
        #Static ndays, lastDay As Long
        # --> 'Static' means value is persistant between calls, ie, retains its value
        ### use class variable to make static
        if Resett < 1:
            G82 = 0.0
            G82o = 0.0 #' changed "G" to "G82" 6/24/99 to keep meas. sep. frm 82
            self._Tp3 = 0.0 # static
            self._Tp2 = 0.0 # static
            self._Tp1 = 0.0 # static
            self._ndays = 0 # static
            self._lastDay = 0 # static
            self._Rn = 0.0  # static ## not explicity initialized in VB.net code, default is 0 from web search

        if timestep > 23:   #' Daily or Monthly Time Step  ' added 10/13/90  start if1
            if self._lastDay < 0.5 or Resett < 1:  #' start if2
                G82 = 0.0
                G82o = 0.0
                GFAO = 0.0
                GFAOr = 0.0
                self._Tp3 = 0.0
                self._Tp2 = 0.0
                self._Tp1 = 0.0
                self._ndays = 0
            else:
                if (self._lastDay == 15 and da == 15) or (self._lastDay == 0 and da == 0):

                    #' monthly heat flux
                    G82 = 0.0 #' assume monthly heat flux is zero
                    G82 = 0.14 * (TMean - self._Tp1) #' added 3/28/94  (use prior month) (FAO)
                    GFAO = G82
                    G82o = G82
                    GFAOr = G82
                else:
                    if self._ndays > 0:
                        G82 = (TMean - (self._Tp3 + self._Tp2 + self._Tp1) / self._ndays) * 0.3768 #' MJ/m2/d
                    else:
                        G82 = 0.0
                    GFAO = 0.0
                    G82o = G82
                    GFAOr = GFAO
                #'  Tp3 = Tp2   ' moved after end of this end if 3/28/94
                #'  Tp2 = Tp1
                #'  Tp1 = TMean
                #'  ndays = ndays + 1
                #'  IF ndays > 3 THEN ndays = 3
            self._lastDay = da
            self._Tp3 = self._Tp2 #' moved here 3/28/94
            self._Tp2 = self._Tp1
            self._Tp1 = TMean
            self._ndays = self._ndays + 1
            if self._ndays > 3: 
                self._ndays = 3

        else: #' hourly time step (assumed)
            if self._Rn >= 0:  #' added 10/13/90  (units are MJ/m2/day, but will be W/m2 on console.writeout)
                #' If Ref < 0.5 Then
                G82o = 0.1 * self._Rn #' Clothier (1986), Kustas et al (1989) in Asrar Remote Sens. Txt
                #' for full cover alfalfa (but high for alfalfa. use for grass
                #' Else
                G82 = 0.04 * self._Rn #' for alfalfa reference based on Handbook Hydrol.
                #' End If
            else:
                #' If Ref < 0.5 Then
                G82o = self._Rn * 0.5 #' R.Allen obersvations for USU Drainage Farm.  Alta Fescue
                #' crop near full cover.  Adj. Soil heat flux assuming that
                #' therm. cond. in top 100 mm was 2 MJ/m2/C.
                #' Else
                G82 = self._Rn * 0.2 #' alfalfa
                #' End If
                #' GFAO = G

            if Rn56 >= 0:      #' added 10/13/90  (units are MJ/m2/day, but will be W/m2 on console.writeout)
                #' If Ref < 0.5 Then
                GFAO = 0.1 * Rn56 #' Clothier (1986), Kustas et al (1989) in Asrar Remote Sens. Txt
                #' for full cover alfalfa (fits grass better than alfalfa.  use for grass)
                #' Else
                GFAOr = 0.04 * Rn56 #' alfalfa reference based on Handbook Hydrol.
                #' End If
            else:
                #' If Ref < 0.5 Then
                GFAO = Rn56 * 0.5 #' R.Allen obersvations for USU Drainage Farm.  Alta Fescue
                #' crop near full cover.  Adj. Soil heat flux assuming that
                #' therm. cond. in top 100 mm was 2 MJ/m2/C.
                #' Else
                GFAOr = Rn56 * 0.2 #' alfalfa
                #' End If

        # these were originally passed in byRef
        return G82,G82o,GFAO,GFAOr



    #' Hargreaves Samani reference ET
    #HargreavesSamani(ByVal TMax As Single, ByVal TMin As Single, ByVal tAvg As Single, ByVal latentHeat As Double, ByVal extRa As Double) As Double
    def HargreavesSamani(self, TMax, TMin, tAvg, latentHeat, extRa):
        """ """
        if TMax < TMin:
            hs = 0.0
        else:
            hs = 0.0023 * (TMax - TMin)**0.5 * extRa * (tAvg + 17.8) #' same units as Ra
        hs = hs / latentHeat * 1000000.0 #' mm/day
        return hs


 
    #' Penman PET's
    '''
    Private Sub Penmans(ByVal lat As Double, ByVal doy As Short, ByVal pressure As Double, ByVal rn56 As Double, _
                ByVal Rn82 As Double, ByVal ed As Double, ByVal ea As Double, ByVal latentHeat As Double, _
                ByVal delta As Double, ByVal gamma As Double, ByVal TMean As Single, ByVal G82 As Double, _
                ByVal G82o As Double, ByVal GFAO As Double, ByVal GFAOr As Double, ByVal U242 As Double, _
                ByRef Penman As Double, ByRef PreTay As Double, ByRef KimbPeng As Double, _
                ByRef ASCEPMstdr As Double, ByRef ASCEPMstdo As Double, ByRef FAO56PM As Double, _
                ByRef KimbPen As Double)
    '''
    def Penmans(self, lat, doy, pressure, rn56, Rn82, ed, ea, latentHeat, delta, gamma, TMean, G82, G82o, GFAO, GFAOr, U242):
        #        Penman, PreTay, KimbPeng, ASCEPMstdr, ASCEPMstdo, FAO56PM, KimbPen):   # this line byRef

        j = doy
        if lat < 0:
            j = doy - 182
            if j < 1: 
                j = j + 365

        ea_TMean = self.aFNEs(TMean)
        Awk = 0.4 + 1.4 * math.exp(-((j - 173) / 58) ** 2)
        Bwk = (0.007 + 0.004 * math.exp(-((j - 243) / 80) ** 2)) * 86.4 #' for m/s
        RnEq = Rn82
        GEq = G82

        #' 1982 Kimberly Penman

        KimbPen = (delta * (RnEq - GEq) + gamma * 6.43 * (ea - ed) * (Awk + Bwk * U242)) / (delta + gamma)
        KimbPen = KimbPen / latentHeat * 1000000.0
        GEq = G82o
        awkg = 0.3 + 0.58 *  math.exp(-((j - 170) / 45) ** 2) #' Wright(1996) for grass
        bwkg = 0.32 + 0.54 * math.exp(-((j - 228) / 67) ** 2) #' for m/s
        KimbPeng = (delta * (RnEq - GEq) + gamma * 6.43 * (ea - ed) * (awkg + bwkg * U242)) / (delta + gamma)
        KimbPeng = KimbPeng / latentHeat * 1000000.0

        #' FAO-56 Penman-Monteith

        gamma56 = 0.000665 * pressure #' kPa/C   may 17 1999
        RnEq = rn56
        GEq = GFAO
        FAO56PM = (0.408 * delta * (RnEq - GEq) + gamma56 * 900 / (TMean + 273) * U242 * (ea - ed)) / (delta + gamma56 * (1 + 0.34 * U242)) #'  may 17 1999 move before ea=fnes(TMean)

        #' Priestley-Taylor added 1/3/08 by Justin Huntington *****************************

        PreTay = 1.26 * (delta / (delta + gamma56) * (RnEq - GEq)) / latentHeat * 1000000.0

        #' Penman 1948 withorig wind Rome wind function added 8/17/09 by Justin Huntington*************************

        #' Penman = ((Delta / (Delta + gamma56) * (RnEq - GEq)) + 6.43 * gamma56 / (Delta + gamma56) * (1 + 0.537 * U242) * (ea - ed))
        Penman = (((delta / (delta + gamma56) * (RnEq - GEq))) / latentHeat * 1000000.0) + ((gamma56 / (delta + gamma56) * (0.26 * (1 + 0.537 * U242)) * ((ea_TMean * 10) - (ed * 10))))

        #' Penman = Penman / latentHeat * 1000000!

        #' Reduced Forms ofASCE-PM (standardized).

        GEq = GFAOr
        ASCEPMstdr = (0.408 * delta * (RnEq - GEq) + gamma56 * 1600 / (TMean + 273) * U242 * (ea - ed)) / (delta + gamma56 * (1 + 0.38 * U242))
        GEq = GFAO
        ASCEPMstdo = (0.408 * delta * (RnEq - GEq) + gamma56 * 900 / (TMean + 273) * U242 * (ea - ed)) / (delta + gamma56 * (1 + 0.34 * U242))

        return  (Penman, PreTay, KimbPeng, ASCEPMstdr, ASCEPMstdo, FAO56PM, KimbPen)


################################################################################ 


def do_tests():
    """ Simple testing of functions as developed """
    o = refET()
    print 'TESTS\n'
    TMean = 51.0
    Heatlt = o.aFNHarrison(TMean)
    print 'aFNHarrison(T=%s):                          %s' % (TMean, Heatlt)

    doy = 50
    latitude = 35.5
    Ra = o.ExtraterrestrialRadiation(doy, latitude)
    print 'ExtraterrestrialRadiation(DoY=%s, lat=%s): %s' % (doy, latitude, Ra)
    Delta = o.aFNDelta(TMean) 
    print 'aFNDelta(T=%s):                             %s' % (TMean, Delta)

    elevm = 1000.
    pressure = o.aFNPressure(elevm=elevm)
    print 'aFNPressure(elevm=%s):                     %s' % (elevm, pressure)
    
    Gamma = o.aFNGamma(pressure, Heatlt) #' kPa/C
    print 'aFNGamma(pressure=%s,Heatlt=%s):        %s' % (pressure, Heatlt, Gamma)

    TDew = 33.0
    ed = o.aFNEs(TDew)
    print
    print 'EstimateClearSkyRadiation(Ra, pressure, ed, latitude, doy)'
    Rso = o.EstimateClearSkyRadiation(Ra, pressure, ed, latitude, doy)
    print 'EstimateClearSkyRadiation(%s,%s,%s,%s,%s):        %s' % (Ra,pressure,ed,latitude,doy,Rso)

    TMax, TMin = 62.0, 34.3
    avgTMax, avgTMin = 60.0, 30.3
    print
    print 'EstimateIncidentRadiation(Rso, TMax, TMin, avgTMax, avgTMin)'
    Rs = o.EstimateIncidentRadiation(Rso, TMax, TMin, avgTMax, avgTMin)
    print 'EstimateIncidentRadiation(%s,%s,%s,%s,%s):        %s' % (Rso, TMax, TMin, avgTMax, avgTMin, Rs)

    print
    print 'FAO56NetRadiation(elevm, latitude, doy, Ra, Rs, Rso, TMax, TMin, ed):   Rn56, Rn82'
    Rn56, Rn82 = o.FAO56NetRadiation(elevm, latitude, doy, Ra, Rs, Rso, TMax, TMin, ed)
    print 'FAO56NetRadiation(%s,%s,%s,%s,%s,%s,%s,%s,%s):  %s, %s' % (elevm, latitude, doy, Ra, Rs, Rso, TMax, TMin, ed, Rn56, Rn82)

    #Resett = -1
    Resett = 0
    da = 3
    #timeStep = 50
    timeStep = 6
    G82, G82o, GFAO, GFAOr = o.ComputeSoilHeat(Resett, da, timeStep, TMean, Rn56)
    print 'ComputeSoilHeat(Resett, da, timeStep, TMean, Rn56):  G82, G82o, GFAO, GFAOr'
    print 'ComputeSoilHeat(%s,%s,%s,%s,%s):  %s, %s, %s, %s' % (Resett, da, timeStep, TMean, Rn56, G82, G82o, GFAO, GFAOr)
    da = 4
    timeStep = 7
    Resett = 2
    G82, G82o, GFAO, GFAOr = o.ComputeSoilHeat(Resett, da, timeStep, TMean, Rn56)
    print 'ComputeSoilHeat(%s,%s,%s,%s,%s):  %s, %s, %s, %s' % (Resett, da, timeStep, TMean, Rn56, G82, G82o, GFAO, GFAOr)

    ea = (o.aFNEs(TMax) + o.aFNEs(TMin)) * 0.5
    u242 = 5   # wind ??
    penman_results = o.Penmans(latitude, doy, pressure, Rn56, Rn82, ed, ea, Heatlt, Delta, Gamma, TMean, G82, G82o, GFAO, GFAOr, u242)
    Penman, PreTay, KimbPeng, ASCEPMstdr, ASCEPMstdo, FAO56PM, KimbPen = penman_results
    print penman_results




################################################################################ 
if __name__ == '__main__':
    ### testing during development
    do_tests()        

