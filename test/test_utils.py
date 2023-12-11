from unittest import TestCase

from slurm_pipeline.utils import secondsToTime


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
