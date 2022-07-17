import unittest

from dve_tests.common.test_common import CommonTest
from dve_tests.config.test_config import ConfigTest
from dve_tests.cli.test_cli import CliTest


def load_test(c):
    return unittest.defaultTestLoader.loadTestsFromTestCase(c)


def all_tests():
    test_suite = unittest.TestSuite()
    test_suite.addTest(load_test(CommonTest))
    test_suite.addTest(load_test(ConfigTest))
    test_suite.addTest(load_test(CliTest))
    return test_suite


if __name__ == "__main__":
    suite = all_tests()
    runner = unittest.TextTestRunner()
    runner.run(suite)
