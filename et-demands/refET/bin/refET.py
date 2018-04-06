import math
import numpy as np

class refET:

    def __init__(self, b0, b1, b2):
        """ """
        
        # Thorton and Running Coefficients
        
        self.TR_b0 = b0
        self.TR_b1 = b1
        self.TR_b2 = b2
        
        # these were defined as 'static' variable within a Function in the VB.net version 
        
        self._Tp3 = 0.0 # static
        self._Tp2 = 0.0 # static
        self._Tp1 = 0.0 # static
        self._ndays = 0 # static
        self._lastDay = 0 # static

    def ComputeRs(self, doy, TMax, TMin, TDew, elevm, latitude, avgTMax, avgTMin): 
        """ Compute estimated incident solar radiation

        Args:
            doy: day of year
            TMax: maximum temperature
            TMin: minimum temperature
            elevm: elevation in meters
            latitude: latitude
            avgTMax: average monthly maximum temperature
            avgTMin: average monthly minimum temperature
            TR_b0: Thronton and Running b0 coefficient
            TR_b1: Thronton and Running b1 coefficient
            TR_b2: Thronton and Running b2 coefficient

        Returns:
            Rs: incident solar radiation
        """
        TAvg = 0.5 * (TMax + TMin)

        # compute extraterrestial radiation and other data needed to compute incident solar radiation

        Ra = self.ExtraterrestrialRadiation(doy, latitude)
        ed = self.aFNEs(TDew)
        pressure = self.aFNPressure(elevm)

        # Estimate clear sky radiation (Rso)
        
        Rso = 0.0
        Rso = self.EstimateClearSkyRadiation(Ra, pressure, ed, latitude, doy)
        Rs = self.EstimateIncidentRadiation(Rso, TMax, TMin, avgTMax, avgTMin)
        return Rs

    def ComputeHargreavesSamaniRefET(self, doy, TMax, TMin, latitude): 
        """ Compute Hargreaves Samani reference ET

        Args:
            doy: day of year
            TMax: maximum temperature
            TMin: minimum temperature
            latitude: latitude

        Returns:
            hsRefET: Hargreaves Samani referencet ET
        """
        TAvg = 0.5 * (TMax + TMin)
        
        # compute latent heat of vaporization

        latentHeat = self.aFNHarrison(TAvg)

        # compute extraterrestial radiation

        Ra = self.ExtraterrestrialRadiation(doy, latitude)
        if TMax < TMin:
            hsRefET = 0.0
        else:
            hsRefET = 0.0023 * (TMax - TMin)**0.5 * Ra * (TAvg + 17.8) # same units as Ra
        hsRefET = hsRefET / latentHeat * 1000000.0 # mm/day
        return hsRefET

    def ComputePenmanRefETs(self, yr, mo, da, doy, time_step, TMax, TMin, TDew, Rs, u24, elevm, latitude):
        """ Compute reference ET by Penman methods

        Args:
            doy: day of year
            yr: year
            mo: month
            da: day
            time_step: time step
            TMax: maximum temperature
            TMin: minimum temperature
            Rs: incident solar radiation
            u24: wind
            elevm: elevation in meters
            latitude: latitude

        Returns:
            Penman, PreTay, KimbPeng, ASCEr, ASCEo, FAO56PM, KimbPen: Penman reference ET's
            hsRefET: Hargreaves Samani referencet ET
        """
        TAvg = 0.5 * (TMax + TMin)

        # compute latent heat of vaporization

        latentHeat = self.aFNHarrison(TAvg)

        # compute extraterrestial radiation

        Ra = self.ExtraterrestrialRadiation(doy, latitude)
        Delta = self.aFNDelta(TAvg) # kPa/C
        ed = self.aFNEs(TDew)
        pressure = self.aFNPressure(elevm)
        Gamma = self.aFNGamma(pressure, latentHeat) # kPa/C

        # Estimate clear sky radiation (Rso)
        
        Rso = 0.0
        Rso = self.EstimateClearSkyRadiation(Ra, pressure, ed, latitude, doy)

        # compute net radiation

        # Rn82 was passed byRef

        Rn56, Rn82 = self.FAO56NetRadiation(elevm, latitude, doy, Ra, Rs, Rso, TMax, TMin, ed)

        # If Ref <= 0.5 Then ht = GrassHt Else ht = AlfHt

        AlfHt = 0.5 # m
        GrassHt = 0.12 # m
        htr = AlfHt
        ht = GrassHt # assume default is grass

        # Assuming weather measurement surface is that of reference

        site_hto = ht
        site_htr = htr

        # set anemometer height

        anemom = 2 # m

        # Theorectical adjustment (Allen) over grass is:
        # d = .67 * GrassHt  'site_ht 'modified 12/21/99 to reflect wind required over grass in std eqns.
        # zom = .123 * GrassHt  'site_ht

        # U242 = U24 * Log((2 - d) / zom) / Log((anemom - 0.67 * site_hto) / (0.123 * site_hto))
        # for Consuse comp, all wind is at 2 m:

        u242 = u24
        U242r = u24

        # 1982 Kimberly Penman

        G82, G82o, GFAO, GFAOr = self.ComputeSoilHeat(da, time_step, TAvg, Rn56, Rn82) # modified 6/24/99
        ea = (self.aFNEs(TMax) + self.aFNEs(TMin)) * 0.5
        penmans = self.Penmans(latitude, doy, pressure, Rn56, Rn82, ed, ea, latentHeat, Delta, Gamma, TAvg, G82, G82o, GFAO, GFAOr, u242)
        # Penman, PreTay, KimbPeng, ASCEPMstdr, ASCEPMstdo, FAO56PM, KimbPen = penmans
        return penmans

    def aFNHarrison(self, TAvg):
        """ Compute latent heat as a function average temperature
        Args:
            TAvg: average temperature
        
        Returns:
            a: latent heat of evaporation
        """
        #aFNHarrison = 2500000.0! - 2360 * TAvg  # '!' forces single precision, numpy Float32 is option if needed                              
        a = 2500000.0 - 2360 * TAvg  # J/Kg   Latent Heat of Vaporization
        return a
        
    # compute extraterresttrial radiaton in MG/M2/day
    
    def ExtraterrestrialRadiation(self, doy, lat):
        """ Compute extraterresttrial radiaton in MG/M2/day
        
        Args:
            doy: day of year
            lat: latitude
        
        Returns:
            etr: extraterresttrial radiaton
        """
        #Dim etr, omega, Dr, latRad, decl As Double
        # Do not shift this algorithm for southern latitude. Correct as is.

        Gsc = 0.08202 # MJ/m2/min

        # [131113] Note:  most of constants below were forced to single precision in VB code
        
        latRad = lat * math.pi / 180.0  # Lat is station latitude in degrees
        decl = 0.4093 * math.sin(2.0 * math.pi * (284.0 + doy) / 365.0)
        omega = 0.5 * math.pi - math.atan((-math.tan(latRad) * math.tan(decl)) / 
                (1.0 - math.tan(decl) * math.tan(decl) * math.tan(latRad) * math.tan(latRad)) ** 0.5)
        Dr = 1.0 + 0.033 * math.cos(2.0 * math.pi * doy / 365.0)
        etr = (24.0 * 60.0 / math.pi) * Gsc * Dr * (omega * math.sin(latRad) * math.sin(decl) + 
                math.cos(latRad) * math.cos(decl) * math.sin(omega))
        return etr

    def aFNDelta(self, TAvg):
        """ Eq. 4 + Eq. 7"""
        a = 4098 * self.aFNEs(TAvg) / (TAvg + 237.3) / (TAvg + 237.3) # kPa/C
        return a

    def aFNEs(self, TDew):
        """ Eq. 7 for saturation vapor pressure from dewpoint temperature"""
        a = 0.6108 * math.exp((17.27 * TDew) / (TDew + 237.3)) # Tetens (1930) equation based
        return a

    def aFNPressure(self, elevation):
        """ Eq. 3 - kPa - Standardized by ASCE 2005"""
        # version converted from vb.net
    
        # return 101.3 * ((293. - 0.0065 * elevation) / 293.) ** (9.8 / (0.0065 * 286.9))
    
        # version from from DRI
    
        # return 101.3 * np.power((293.0 - 0.0065 * elevation) / 293.0, 5.26)

        # version extended to better match vb.net version
        # 5.255114352 = 9.8 / (0.0065 * 286.9
     
        return 101.3 * np.power((293.0 - 0.0065 * elevation) / 293.0, 5.255114352)

    def aFNGamma(self, Pressure, latentHeat):
        """ Eq. ? """
        a = 1013 * Pressure / 0.622 / latentHeat # kPa/C  cp=1013 J/Kg/C
        return a

    def EstimateClearSkyRadiation(self, extRa, pressure, ed, latDeg, doy):
        """ Estimate clear sky radiation (Rso) using Appendix D method of ASCE-EWRI (2005)
        
        Args:
            extRa: extraterresttrial radiaton
            pressure: air pressure
            ed: saturation vapor pressure
            latDeg: latitude
            doy: day of year
        
        Returns:
            csRSo: clear sky radiaton
        """
        waterInAtm = 0.14 * ed * pressure + 2.1 # mm as of 9/2000 (was cm)
        latRad = latDeg * math.pi / 180
        kturb = 1.0
        sinphi24 = math.sin(0.85 + 0.3 * latRad * math.sin(2 * math.pi / 365 * doy - 1.39) - 0.42 * latRad * latRad)
        kbeam = 0.98 * math.exp((-0.00146 * pressure) / (kturb * sinphi24) - 0.075 * (waterInAtm / sinphi24) ** 0.4) # modified 9/25/2000
        if kbeam < 0.15:
            kdiffuse = 0.18 + 0.82 * kbeam
        else:
            kdiffuse = 0.35 - 0.36 * kbeam
        csRSo = (kbeam + kdiffuse) * extRa
        return csRSo

    def EstimateIncidentRadiation(self, csRSo, maxT, minT, monMaxT, monMinT, 
                                  TR_b0 = None, TR_b1 = None, TR_b2 = None):
        """ Estimate incident radiation using equation 14
        
        Args:
            csRSo: clear sky radiaton
            maxT: maximum temperature
            minT: maximum temperature
            monMaxT: average monthly maximum temperature
            monMinT: average monthly minimum temperature
            TR_b0: Thronton and Running b0 coefficient
            TR_b1: Thronton and Running b1 coefficient
            TR_b2: Thronton and Running b2 coefficient
        
        Returns:
            incRs: incident radiaton
        """

        dt = maxT - minT          # temp difference in C
        dtMon = monMaxT - monMinT # long term monthly temp difference in C
        dt = max(0.1, dt)
        dtMon = max(0.1, dtMon)

        # Orginally used UI determined function for coefficient B based on arid stations in T-R paper
        # BTR = 0.023 + 0.1 * System.Math.Exp(-0.2 * dtMon)
        # Changed to use user specified values 11/21/2012.
        # Changed input of third Thorton and Running coefficient to include sign 08/22/2013.
        # Enabled TR coefficients to be node specific - dlk - 01/20/2016.

        if TR_b0 is None: TR_b0 = self.TR_b0
        if TR_b1 is None: TR_b1 = self.TR_b1
        if TR_b2 is None: TR_b2 = self.TR_b2
        BTR = TR_b0 + TR_b1 * math.exp(TR_b2 * dtMon)

        # estimate daily Rs using Thornton and Running method (added Nov. 1, 2006)
        # incRs = csRSo * (1 - 0.9 * math.exp(-BTR * dt ** 1.5))
        # from Eq. 14
        incRs = csRSo * (1 - 0.9 * math.exp(-BTR * dt ** 1.5))
        return incRs
    
    def FAO56NetRadiation(self, elevation, lat, doy, etRa, incRs, csRSo, maxT, minT, ed):
        """ Computes FAO 56 Net Radiation
        
        Args:
            elevation: elevation in meters
            latitude: latitude
            doy: day of year
            etRa: extraterresttrial radiaton
            incRs: incident radiation
            csRSo: clear sky radiaton
            TMax: maximum temperature
            TMin: maximum temperature
            ed: saturation vapor pressure
        
        Returns:
            FAO56NR: FA056 net radiation
            Rn82: Rn82 net radiation
        """
        j = doy
        if lat < 0:
            j = doy - 182
            if j < 1:
                j = j + 365
        Rna1 = 0.26 + 0.1 * math.exp(-(0.0154 * (j - 180)) ** 2)
        Rso75 = 0.75 * etRa
        Rso56 = (0.75 + 0.00002 * elevation) * etRa # 4/6/94
        if csRSo > 0:
            RsRso = incRs / csRSo # 24-hours
        else:
            RsRso = 0.7
        if Rso56:
            RsRso56 = incRs / Rso56 # 24-hours
        else:
            RsRso56 = 0.7
        RsRso = max(0.2, min(RsRso, 1.0))
        RsRso56 = max(0.2, min(RsRso56, 1.0))
        RsRso2use = RsRso # useRso based on sun angle and water vapor as of 9/25/2000
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

        # FAO 56 Net Radiation computation

        Rbo56 = 0.000000004903 * 0.5 * ((maxT + 273.16) ** 4 + (minT + 273.16) ** 4) * (0.34 - 0.14 * math.sqrt(ed))
        Rnl56 = (1.35 * RsRso2use - 0.35) * Rbo56
        FAO56NR = (1 - 0.23) * incRs - Rnl56
        return FAO56NR, Rn82

    # soil heat flux
    
    def ComputeSoilHeat(self, da, time_step, TAvg, Rn56, Rn82): # modified 6/24/99
        """ Computes soil heat flux
        
        Args:
            da: day
            time_step: time step
            TAvg: average temperature
            Rn56: FAO56 net radiation
            Rn82: Rn82 net radiation
        
        Returns:
            G82: 
            G82o: 
            GFAO: 
            GFAOr: 
        """
        # ByRef G82 As Double, ByRef G82o As Double, ByRef GFAO As Double, ByRef GFAOr As Double
        # Static Tp3, Tp1, Tp2 As Double
        # Static ndays, lastDay As Long
        # --> 'Static' means value is persistant between calls, ie, retains its value
        # use class variable to make static
        if time_step == 'day':   # Daily or Monthly Time Step  ' added 10/13/90  start if1
            if self._lastDay < 1:  # start if2
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
                    # monthly heat flux
                    
                    G82 = 0.0 # assume monthly heat flux is zero
                    G82 = 0.14 * (TAvg - self._Tp1) # added 3/28/94  (use prior month) (FAO)
                    GFAO = G82
                    G82o = G82
                    GFAOr = G82
                else:
                    if self._ndays > 0:
                        G82 = (TAvg - (self._Tp3 + self._Tp2 + self._Tp1) / self._ndays) * 0.3768 # MJ/m2/d
                    else:
                        G82 = 0.0
                    GFAO = 0.0
                    G82o = G82
                    GFAOr = GFAO
                #  Tp3 = Tp2   ' moved after end of this end if 3/28/94
                #  Tp2 = Tp1
                #  Tp1 = TAvg
                #  ndays = ndays + 1
                #  IF ndays > 3 THEN ndays = 3
            self._lastDay = da
            self._Tp3 = self._Tp2 # moved here 3/28/94
            self._Tp2 = self._Tp1
            self._Tp1 = TAvg
            self._ndays = self._ndays + 1
            self._ndays = min(self._ndays, 3)
        else: # hourly time step (assumed)
            # changed Rn to Rn82 dlk 01/27/2016

            if Rn82 >= 0:  # added 10/13/90  (units are MJ/m2/day, but will be W/m2 on console.writeout)
                # If Ref < 0.5 Then
                G82o = 0.1 * Rn82 # Clothier (1986), Kustas et al (1989) in Asrar Remote Sens. Txt

                # for full cover alfalfa (but high for alfalfa. use for grass

                # Else
                G82 = 0.04 * Rn82 # for alfalfa reference based on Handbook Hydrol.
                # End If
            else:
                # If Ref < 0.5 Then
                G82o = Rn82 * 0.5 # R.Allen obersvations for USU Drainage Farm.  Alta Fescue

                # crop near full cover.  Adj. Soil heat flux assuming that
                # therm. cond. in top 100 mm was 2 MJ/m2/C.

                # Else
                G82 = Rn82 * 0.2 # alfalfa
                # End If
                # GFAO = G
            if Rn56 >= 0:      # added 10/13/90  (units are MJ/m2/day, but will be W/m2 on console.writeout)
                # If Ref < 0.5 Then
                GFAO = 0.1 * Rn56 # Clothier (1986), Kustas et al (1989) in Asrar Remote Sens. Txt
                
                # for full cover alfalfa (fits grass better than alfalfa.  use for grass)
                
                # Else
                GFAOr = 0.04 * Rn56 # alfalfa reference based on Handbook Hydrol.
                # End If
            else:
                # If Ref < 0.5 Then
                GFAO = Rn56 * 0.5 # R.Allen obersvations for USU Drainage Farm.  Alta Fescue
                
                # crop near full cover.  Adj. Soil heat flux assuming that
                # therm. cond. in top 100 mm was 2 MJ/m2/C.
                
                # Else
                GFAOr = Rn56 * 0.2 # alfalfa
                # End If
        return G82, G82o, GFAO, GFAOr

    def Penmans(self, lat, doy, pressure, Rn56, Rn82, ed, ea, latentHeat, delta, gamma, TAvg, G82, G82o, GFAO, GFAOr, U242):
        """ Compute Penman based reference ET's
        
        Args:
            lat: latitude
            doy: day of year
            pressure: air pressure
            Rn56: FAO56 net radiation
            Rn82: Rn82 net radiation
            ed: saturation vapor pressure
            latentHeat: latent heat of evaporation
            gamma:
            TAvg: average temperature
            G82: 
            G82o: 
            GFAO: 
            GFAOr: 
            U242: wind
        
        Returns:
            Penman, PreTay, KimbPeng, ASCEr, ASCEo, FAO56PM, KimbPen: Penman reference ET's
        """
        zero = 0.0
        j = doy
        if lat < 0:
            j = doy - 182
            if j < 1: 
                j = j + 365
        ea_TAvg = self.aFNEs(TAvg)
        Awk = 0.4 + 1.4 * math.exp(-((j - 173) / 58) ** 2)
        Bwk = (0.007 + 0.004 * math.exp(-((j - 243) / 80) ** 2)) * 86.4 # for m/s
        RnEq = Rn82
        GEq = G82

        # 1982 Kimberly Penman

        KimbPen = (delta * (RnEq - GEq) + gamma * 6.43 * (ea - ed) * (Awk + Bwk * U242)) / (delta + gamma)
        KimbPen = KimbPen / latentHeat * 1000000.0
        KimbPen = max(KimbPen, zero)
        GEq = G82o
        awkg = 0.3 + 0.58 *  math.exp(-((j - 170) / 45) ** 2) # Wright(1996) for grass
        bwkg = 0.32 + 0.54 * math.exp(-((j - 228) / 67) ** 2) # for m/s
        KimbPeng = (delta * (RnEq - GEq) + gamma * 6.43 * (ea - ed) * (awkg + bwkg * U242)) / (delta + gamma)
        KimbPeng = KimbPeng / latentHeat * 1000000.0
        KimbPeng = max(KimbPeng, zero)

        # FAO-56 Penman-Monteith

        gamma56 = 0.000665 * pressure # kPa/C   May 17 1999
        RnEq = Rn56
        GEq = GFAO
        FAO56PM = (0.408 * delta * (RnEq - GEq) + gamma56 * 900 / (TAvg + 273) * U242 * (ea - ed)) / (delta + gamma56 * (1 + 0.34 * U242)) #  may 17 1999 move before ea=fnes(TAvg)
        FAO56PM = max(FAO56PM, zero)

        # Priestley-Taylor added 1/3/08 by Justin Huntington

        PreTay = 1.26 * (delta / (delta + gamma56) * (RnEq - GEq)) / latentHeat * 1000000.0
        PreTay = max(PreTay, zero)

        # Penman 1948 withorig wind Rome wind function added 8/17/09 by Justin Huntington

        # Penman = ((Delta / (Delta + gamma56) * (RnEq - GEq)) + 6.43 * gamma56 / (Delta + gamma56) * (1 + 0.537 * U242) * (ea - ed))
        Penman = (((delta / (delta + gamma56) * (RnEq - GEq))) / latentHeat * 1000000.0) + ((gamma56 / (delta + gamma56) * (0.26 * (1 + 0.537 * U242)) * ((ea_TAvg * 10) - (ed * 10))))
        Penman = max(Penman, zero)

        # Penman = Penman / latentHeat * 1000000!

        # Reduced Forms ofASCE-PM (standardized).

        GEq = GFAOr
        ASCEPMstdr = (0.408 * delta * (RnEq - GEq) + gamma56 * 1600 / (TAvg + 273) * U242 * (ea - ed)) / (delta + gamma56 * (1 + 0.38 * U242))
        ASCEPMstdr = max(ASCEPMstdr, zero)
        GEq = GFAO
        ASCEPMstdo = (0.408 * delta * (RnEq - GEq) + gamma56 * 900 / (TAvg + 273) * U242 * (ea - ed)) / (delta + gamma56 * (1 + 0.34 * U242))
        ASCEPMstdo = max(ASCEPMstdo, zero)
        return  (Penman, PreTay, KimbPeng, ASCEPMstdr, ASCEPMstdo, FAO56PM, KimbPen)

############## 

def do_tests():
    """ Simple testing of functions as developed """
    o = refET()
    print 'TESTS\n'
    TAvg = 51.0
    latentHeat = o.aFNHarrison(TAvg)
    print 'aFNHarrison(T=%s):                          %s' % (TAvg, latentHeat)

    doy = 50
    latitude = 35.5
    Ra = o.ExtraterrestrialRadiation(doy, latitude)
    print 'ExtraterrestrialRadiation(doy = %s, lat = %s): %s' % (doy, latitude, Ra)
    Delta = o.aFNDelta(TAvg) 
    print 'aFNDelta(T=%s):                             %s' % (TAvg, Delta)

    elevm = 1000.
    pressure = o.aFNPressure(elevm=elevm)
    print 'aFNPressure(elevm=%s):                     %s' % (elevm, pressure)
    
    Gamma = o.aFNGamma(pressure, latentHeat) # kPa/C
    print 'aFNGamma(pressure=%s,latentHeat=%s):        %s' % (pressure, latentHeat, Gamma)

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

    da = 3
    # time_step = 'hour'
    time_step = 'day'
    G82, G82o, GFAO, GFAOr = o.ComputeSoilHeat(da, time_step, TAvg, Rn56)
    print 'ComputeSoilHeat(%s,%s,%s,%s,%s):  %s, %s, %s, %s' % (da, time_step, TAvg, Rn56, G82, G82o, GFAO, GFAOr)

    ea = (o.aFNEs(TMax) + o.aFNEs(TMin)) * 0.5
    u242 = 5   # wind ??
    penman_results = o.Penmans(latitude, doy, pressure, Rn56, Rn82, ed, ea, latentHeat, Delta, Gamma, TAvg, G82, G82o, GFAO, GFAOr, u242)
    Penman, PreTay, KimbPeng, ASCEPMstdr, ASCEPMstdo, FAO56PM, KimbPen = penman_results
    print penman_results

if __name__ == '__main__':
    # testing during development
    do_tests()        

