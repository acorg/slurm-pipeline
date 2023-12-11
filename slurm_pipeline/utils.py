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
