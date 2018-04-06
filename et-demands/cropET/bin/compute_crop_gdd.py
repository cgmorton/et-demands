def compute_crop_gdd(crop, foo, foo_day):
    """Compute crop growing degree days

    Args:
        crop ():
        foo ():
        foo_day ():

    Returns:
        None
    """

    # Calculate 30 day ETr each year
    # Shift entries in 30 day array to add today's ETref

    etref_lost = 0.0
    if foo_day.sdays > 30:
        etref_lost = foo_day.etref_array[0]
        for idx in range(29):    # idx = 1 is 30 days ago
            foo_day.etref_array[idx] = foo_day.etref_array[idx + 1]
        foo_day.etref_array[29] = foo_day.etref
        foo.etref_30 = foo.etref_30 + (foo_day.etref - etref_lost) / 30.
    else:
        foo_day.etref_array[foo_day.sdays-1] = foo_day.etref
        foo.etref_30 = (foo.etref_30 * (foo_day.sdays - 1) + foo_day.etref) / foo_day.sdays

    # Reset CGDD if new year
    # For all crops, but winter grain, reset CGDD counter on cropGDDTriggerDoy
    # (formerly hard wired to Jan 1 or Oct 1)
    # ctCount = 13 and 14 are winter grain (irrigated and non-irrigated)

    # winter grain '<------ specific value for crop number, changed to two ww crops Jan 07

    if (crop.winter_crop and
        (foo_day.doy_prev < crop.gdd_trigger_doy and
         foo_day.doy >= crop.gdd_trigger_doy)):
        foo.cgdd = 0.0
        foo.doy_start_cycle = 0   # DOY 0 - reset planting date also
        foo.real_start = False    # April 12, 2009 rga
        foo.in_season = False     # July 30, 20120 dlk
    elif (not crop.winter_crop and
          (foo_day.doy_prev > (crop.gdd_trigger_doy + 199) and
           foo_day.doy < (crop.gdd_trigger_doy + 199))):
        foo.cgdd = 0.0
        foo.doy_start_cycle = 0   # DoY 0 - reset planting date also
        foo.real_start = False    # April 12, 2009 rga
        foo.in_season = False     # July 30, 20120 dlk
    foo_day.doy_prev = foo_day.doy

    # Calculate CGDD since trigger date
    # Only needed if a crop

    if crop.curve_number > 0:
        # Use general GDD basis except for corn (crop types 7 thru 10), which require 86-50 method.
        # evaluate winter grain separately because of penalties during winter
        # Development of winter grain is followed through winter,
        # beginning with an assumed October 1 planting in Northern hemisphere
        # Any periods during winter with favourable growing conditions are assumed to
        # advance development of winter grain crop subject to following conditions:
        # Initial GDD calculation is TMean - Tbase if TMean > Tbase, or 0 otherwise.
        # GDD is set to zero if TMin for that day is less than -3 C to account
        # for negative impacts of freezing.
        # In addition, subtract 10 GDD from daily GDD if TMin of previous day < -5 C to
        # account for retardation (stunning) that carries over into next day.
        # Minimum adjusted GDD for any day is 0.
        # If TMin for day is < -25 C (very cold temperature) and no snow cover,
        # burning of leaves is assumed to occur and CGDD is reduced.
        # On first day following -25 C TMin, CGDD prior to day is reduced by 30%.

        if crop.winter_crop:
            # Winter wheat or winter grain

            if foo_day.tmin < -4.0:
                # No growth if < -3C (was -3, now -4)

                foo.gdd = 0.0
            elif foo_day.tmean > crop.tbase:
                # Simple method for all other crops

                foo.gdd = foo_day.tmean - crop.tbase
            else:
                foo.gdd = 0.0
            foo.gdd -= foo.gdd_penalty
            foo.gdd = max(foo.gdd, 0.0)
            foo.cgdd += foo.gdd - foo.cgdd_penalty
            foo.cgdd = max(0.0, foo.cgdd)

            # Set up for tommorrow's penalties for winter grain
            # Set up for tomorrow's penalty for low TMin today (was 10), TMin was -5

            if foo_day.tmin < -10:
                foo.gdd_penalty = 5.0
            else:
                foo.gdd_penalty = 0.0
            if foo_day.tmin < -25 and foo_day.snow_depth <= 0:
                # Turn back on winter grain from severe cold if no snow cover (was 0.3)

                foo.cgdd_penalty = foo.cgdd * 0.1
            else:
                foo.cgdd_penalty = 0.0
        elif crop.tbase < 0:
            # Corn

            tmax_prev = foo_day.tmax
            tmin_prev = foo_day.tmin

            # TMax and TMin are subject to Tbase limits for corn

            if foo_day.tmax > 30:
                tmax_prev = 30

            # And to maximum limits for corn

            if foo_day.tmin > 30:
                tmin_prev = 30

            # sub tbase since it is artificially negative for corn as a flag

            if foo_day.tmax < -crop.tbase:
                tmax_prev = -crop.tbase
            if foo_day.tmin < -crop.tbase:
                tmin_prev = -crop.tbase
            tmean_prev = 0.5 * (tmax_prev + tmin_prev)

            # Add tbase since it is artificially set negative as an indicator

            foo.cgdd += tmean_prev + crop.tbase
        elif foo_day.tmean > crop.tbase:
            # Simple method for all other crops

            foo.gdd = foo_day.tmean - crop.tbase
            foo.cgdd += foo.gdd
