
def open_water_evap(foo, foo_day):
    """Calculate open water evaporation

    For deep lakes and reservoirs apply an aerodynamic approach
      based on Allen and Tasumi (2005)
    Called by KcbDaily    
    12/11/2011 - dlk Changed this code to a function and
      added a catch of failure to keep code running.
    """
    # print 'in open_water_evap()'
    Ts_Ta_water = [0., 4., 3., 1., 0., 0., 0., 0., 1., 1., 3., 4., 4.]

    try:                 
        # Estimate water temperature
        # Interpolate value for Ts-Ta
        MoaFrac = foo_day.monthOfCalcs + (foo_day.dayOfCalcs - 15) / 30.4
        if MoaFrac < 1:
            MoaFrac = 1
        if MoaFrac > 12:
            MoaFrac = 12
        Moabase = int(MoaFrac)
        Ts_Ta = Ts_Ta_water[Moabase] + (Ts_Ta_water[Moabase + 1] - Ts_Ta_water[Moabase]) * (MoaFrac - Moabase)
        Ts = foo_day.TMean + Ts_Ta
        vapor_pressure_water = 0.6108 * math.exp((17.27 * Ts) / (Ts + 237.3))
        vapor_pressure_air = 0.6108 * math.exp((17.27 * foo_day.TDew) / (foo_day.TDew + 237.3))
        q_water = 0.622 * vapor_pressure_water / (foo.Pressure - 0.378 * vapor_pressure_water)
        q_air = 0.622 * vapor_pressure_air / (foo.Pressure - 0.378 * vapor_pressure_air)
        Ce = 0.0015
                    
        # Virtual temperature          
        Tv = (foo_day.TMean + 273.16) / (1 - 0.378 * vapor_pressure_air / foo.Pressure)
        # Density in kilograms/m3  (P in kPa)
        density = 3.486 * foo.Pressure / Tv 
        # LE in megawatts/m2
        LE = 2.45 * density * Ce * wind * (q_water - q_air) 
        # Kg/m2/d = mm/d
        ET = LE / 2.45 * 86400 
        # ETr changed to ETref 12/26/2007
        if foo_day.ETref > 0.03:     
            return ET / foo_day.ETref
        else:
            # Substitute if ETr or ETo is too close to zero or negative
            return 0.4
    except:
        # Substitute if ETr or ETo is too close to zero or negative
        return 0.4



