import logging
import datetime
import unittest
import sys

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

log = logging.getLogger(__name__)

CHECK_EXISTING = False


class CommonTest(unittest.TestCase):
    warnings_no = 0

    def test_default_data_home_defined(self):
        log.debug("+++ test common logging:" + str(datetime.datetime.now()))
        self.assertTrue(True)

    def setUp(self):
        # self.conf_dir = os.environ['CONFIG_DIR']
        pass

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
