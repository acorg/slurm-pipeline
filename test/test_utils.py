from unittest import TestCase

from slurm_pipeline.utils import secondsToTime, elapsedToSeconds


class TestSecondsToTime(TestCase):
    """
    Tests for the secondsToTime function.
    """

    def testArbitraryTime(self):
        """
        The secondsToTime function must return the expected value.
        """
        self.assertEqual("2016-12-10 14:20:58", secondsToTime(1481379658.5455897))

    def testArbitraryTimeInSacctFormat(self):
        """
        The secondsToTime function must return the expected value when
        asked for a string compatible with the sacct -S option.
        """
        self.assertEqual(
            "2016-12-10T14:20:58",
            secondsToTime(1481379658.5455897, sacctCompatible=True),
        )


class TestElapsedToSeconds(TestCase):
    """
    Test the elapsedToSeconds function.
    """

    def testZero(self):
        """
        No time at all must be zero seconds.
        """
        self.assertEqual(0, elapsedToSeconds("00:00:00"))

    def testOneHour(self):
        """
        One hour must be 3600 seconds.
        """
        self.assertEqual(3600, elapsedToSeconds("01:00:00"))

    def testOneHourOneMinuteOneSecond(self):
        """
        One hour, one minute and one seconds must be 3661 seconds.
        """
        self.assertEqual(3661, elapsedToSeconds("01:01:01"))

    def testOneDay1(self):
        """
        One day must be 86400 seconds.
        """
        self.assertEqual(86400, elapsedToSeconds("24:00:00"))

    def testOneDay2(self):
        """
        One day must be 86400 seconds.
        """
        self.assertEqual(86400, elapsedToSeconds("1-00:00:00"))
