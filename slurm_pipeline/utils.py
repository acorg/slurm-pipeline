from time import gmtime, strftime


def secondsToTime(seconds, sacctCompatible=False):
    """
    Convert a number of seconds to a time string.

    @param seconds: A C{float} number of seconds since the epoch, in UTC.
    @param sacctCompatible: If C{True}, return a string that can be given to
        sacct with the -S option.
    @return: A C{str} giving the date/time corresponding to C{seconds}.
    """
    return strftime(
        "%Y-%m-%d" + ("T" if sacctCompatible else " ") + "%H:%M:%S", gmtime(seconds)
    )


def elapsedToSeconds(elapsed):
    """
    Convert an "elapsed" string (from sacct) to a number of seconds.

    @param elapsed: A C{str}, either as HH:MM:SS or DD-HH:MM:SS
    @return: An C{int} number of seconds.
    """
    fields = elapsed.split("-")
    if len(fields) == 1:
        daysSeconds = 0
        hms = fields[0]
    else:
        assert len(fields) == 2
        daysSeconds = int(fields[0]) * 24 * 60 * 60
        hms = fields[1]

    h, m, s = map(int, hms.split(":"))

    return daysSeconds + h * 60 * 60 + m * 60 + s
