import util

def open_water_evap(cell, foo_day):
    """Calculate open water evaporation

    For deep lakes and reservoirs apply an aerodynamic approach
        based on Allen and Tasumi (2005)
    Called by kcb_daily.kcb_daily()
    Air pressure was coming from foo.pressure,
        but foo.pressure is initialized to 0 and never computed
    Air pressure is now computed once in et_cell.init_properties_from_row()
        for each station/cell

    """
    ts_ta_water = [0., 4., 3., 1., 0., 0., 0., 0., 1., 1., 3., 4., 4.]

    try:
        # Estimate water temperature
        # Interpolate value for Ts-Ta

        moa_frac = min(max(foo_day.month + (foo_day.day - 15) / 30.4, 1), 12)
        moa_base = int(moa_frac)
        ts_ta = (
            ts_ta_water[moa_base] +
            (ts_ta_water[moa_base + 1] - ts_ta_water[moa_base]) *
            (moa_frac - moa_base))
        ts = foo_day.tmean + ts_ta

        # For now convert to floats since function is called for every time step

        vapor_pressure_water = float(util.es_from_t(ts))
        vapor_pressure_air = float(util.es_from_t(foo_day.tdew))
        q_water = util.q_from_ea(vapor_pressure_water, cell.air_pressure)
        q_air = util.q_from_ea(vapor_pressure_air, cell.air_pressure)

        # Virtual temperature

        tv = (
            (foo_day.tmean + 273.16) /
            (1 - 0.378 * vapor_pressure_air / cell.air_pressure))

        # Density in kilograms/m3  (P in kPa)

        density = 3.486 * cell.air_pressure / tv

        # LE in megawatts/m2
        
        ce = 0.0015
        # DEADBEEF - wind variable is not defined
        le = 2.45 * density * ce * wind * (q_water - q_air)

        # Kg/m2/d = mm/d
        et = le / 2.45 * 86400

        # ETr changed to ETref 12/26/2007

        if foo_day.etref > 0.03:
            return et / foo_day.etref
        else:
            # Substitute if ETr or ETo is too close to zero or negative
            return 0.4
    except:
        # Substitute if ETr or ETo is too close to zero or negative
        return 0.4
