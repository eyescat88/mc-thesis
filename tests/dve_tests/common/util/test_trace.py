import logging
import datetime
import unittest
import sys
import time
import random

from dve.common.util.trace import trace_logger


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

log = logging.getLogger(__name__)


class TraceUtilTest(unittest.TestCase):
    warnings_no = 0

    DELAY_DEFAULT = 0.1

    def rand(self, value):
        return (random.random() + 0.5) * value

    def sleep(self, delay=DELAY_DEFAULT):
        if delay > 0:
            d = self.rand(delay)
            time.sleep(d)

    # @unittest.skip
    def test_trace_callee(self):
        log.debug("+++ test trace callee:" + str(datetime.datetime.now()))

        trc = trace_logger("test-trace", item_samples=1)

        with trc:

            self.sleep()
            trc.update(1)

            self.sleep()
            trc.update(1)

            with trc:

                for _ in range(3):
                    self.sleep()
                    trc.update(1)

                with trc:

                    for _ in range(5):
                        self.sleep()
                        trc.update(1)

            self.sleep()
            trc.update(1)

            with trc:

                for _ in range(2):
                    self.sleep()
                    trc.update(1)

            self.sleep()
            trc.update(1)

        self.assertTrue(True)

    @unittest.skip
    def test_trace_updates(self):
        log.debug("+++ test trace updates:" + str(datetime.datetime.now()))

        trc = trace_logger("test-trace", item_samples=1500)

        with trc:

            with trc:

                trc.update(1000)
                trc.update(1000)

                with trc:

                    for _ in range(50000):
                        trc.update()

                trc.update(10)

                with trc:

                    trc.all()

                    for _ in range(20):
                        trc.update(3)

                trc.update(1000)

        self.assertTrue(True)

    @unittest.skip
    def test_trace_summaries(self):
        log.debug("+++ test trace summaries:" + str(datetime.datetime.now()))

        trc = trace_logger("test-trace")

        with trc:

            with trc:

                trc.update(1000)
                trc.update(1000)

                with trc:

                    for _ in range(50000):
                        trc.update()

                trc.update(10)

                with trc:

                    trc.all()

                    for _ in range(20):
                        trc.update(3)

                trc.update(1000)

        self.assertTrue(True)

    @unittest.skip
    def test_trace_context(self):
        log.debug("+++ test trace context:" + str(datetime.datetime.now()))

        trc = trace_logger("test-trace", item_samples=1500)

        with trc:

            trc.ctx()["A"] = "a1"

            with trc:

                trc.ctx()["B"] = "b1"

                trc.update(1000)
                trc.update(1000)

                with trc:

                    trc.ctx()["C"] = "c1"

                    for _ in range(5000):
                        trc.update()

                trc.update(10)

                with trc:

                    trc.all()

                    trc.ctx()["C"] = "c2"

                    for _ in range(20):
                        trc.update(3)

                trc.update(1000)

        self.assertTrue(True)

    @unittest.skip
    def test_trace_verbose(self):
        log.debug("+++ test trace verbose:" + str(datetime.datetime.now()))

        trc = trace_logger("test-trace", item_samples=1500, verbose=1)

        with trc:

            trc.ctx()["A"] = "a1"

            with trc:

                trc.ctx()["B"] = "b1"

                trc.update(1000)
                trc.update(1000)

                with trc:

                    trc.ctx()["C"] = "c1"

                    for _ in range(5000):
                        trc.update()

                trc.update(10)

                with trc:

                    trc.all()

                    trc.ctx()["C"] = "c2"

                    for _ in range(20):
                        trc.update(3)

                trc.update(1000)

        self.assertTrue(True)

    def setUp(self):
        # self.conf_dir = os.environ['CONFIG_DIR']
        pass

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
