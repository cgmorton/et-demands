
def OpenWaterEvaporation(foo, foo_day):
    """ """
    # print 'in OpenWaterEvaporation()'

    #' For deep lakes and reservoirs
    #' apply an aerodynamic approach based on Allen and Tasumi (2005)
    #' parameters Ts_Ta_water(12), midMonthDOY(12)
    #' called by KcbDaily    
    #' 12/11/2011    dlk Changed this code to a function and added a catch of failure to keep code running.
                        
    #Private Function OpenWaterEvaporation() As Double
    #    Dim ET, LE, Tv, Ce, q_air, q_water As Double
    #    Dim vapor_pressure_air, vapor_pressure_water, Ts, Ts_Ta, Moabase As Double
    #    Dim MoaFrac As Double #' need to compare equations against spreadsheet computations for Am.Falls


    # from modCropET.vb:    Private Ts_Ta_water() As Double = {0, 4, 3, 1, 0, 0, 0, 0, 1, 1, 3, 4, 4}
    Ts_Ta_water = [0., 4., 3., 1., 0., 0., 0., 0., 1., 1., 3., 4., 4.]


    try:             
            
        #' estimate water temperature

        #' interpolate value for Ts-Ta

        MoaFrac = foo_day.monthOfCalcs + (foo_day.dayOfCalcs - 15) / 30.4
        if MoaFrac < 1:     MoaFrac = 1
        if MoaFrac > 12:     MoaFrac = 12
        Moabase = int(MoaFrac)
        Ts_Ta = Ts_Ta_water[Moabase] + (Ts_Ta_water[Moabase + 1] - Ts_Ta_water[Moabase]) * (MoaFrac - Moabase)
        Ts = foo_day.TMean + Ts_Ta
        vapor_pressure_water = 0.6108 * math.exp((17.27 * Ts) / (Ts + 237.3))
        vapor_pressure_air = 0.6108 * math.exp((17.27 * foo_day.TDew) / (foo_day.TDew + 237.3))
        q_water = 0.622 * vapor_pressure_water / (foo.Pressure - 0.378 * vapor_pressure_water)
        q_air = 0.622 * vapor_pressure_air / (foo.Pressure - 0.378 * vapor_pressure_air)
        Ce = 0.0015
                    
        #' virtual temperature
                    
        Tv = (foo_day.TMean + 273.16) / (1 - 0.378 * vapor_pressure_air / foo.Pressure)
        density = 3.486 * foo.Pressure / Tv #' kilograms/m3    (P in kPa)
        LE = 2.45 * density * Ce * wind * (q_water - q_air) #' in megawatts/m2
        ET = LE / 2.45 * 86400 #' Kg/m2/d = mm/d
        if foo_day.ETref > 0.03:     #' ETr changed to ETref 12/26/2007
            return ET / foo_day.ETref
        else:
            return 0.4 #' substitute if ETr or ETo is too close to zero or negative

    except:
        return 0.4 #' substitute if ETr or ETo is too close to zero or negative


"""
"""


