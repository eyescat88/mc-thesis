from decimal import Decimal
from textwrap import dedent
import re
from datetime import datetime

from dve.common.util.time import timer


import logging


def getLogger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    # logget.setLevel(logging.INFO)
    return logger


log = getLogger()


def to_json_oneline(text):
    return re.sub(
        r'Decimal\("([^)]+)"\)',
        r"\1",
        dedent(text).replace("\n", " ").replace("'", '"'),
    )


class TraceInterval:
    def __init__(self, elapsed_time=0, item_count=0):
        self.elapsed_time = elapsed_time
        self.item_count = item_count
        self.frozen = False

    def __add__(self, other):
        elapsed_time = self.elapsed_time + other.elapsed_time
        item_count = self.item_count + other.item_count
        return TraceInterval(elapsed_time, item_count)

    def __radd__(self, other):
        if other == 0:
            return self
        else:
            return self.__add__(other)

    def __sub__(self, other):
        elapsed_time = self.elapsed_time - other.elapsed_time
        item_count = self.item_count - other.item_count
        return TraceInterval(elapsed_time, item_count)

    def __str__(self):
        elapsed_time = self.elapsed_time
        item_count = self.item_count
        if self.frozen:
            return f'{{ "n": {item_count}, "ms": {int(elapsed_time*1000)} }}'
        else:
            return f'{{ "i": {item_count}, "ms": {int(elapsed_time*1000)} }}'

    def to_dict(self):
        return dict(
            i=self.item_count,
            ms=int(self.elapsed_time * 1000),
            hz=Decimal.from_float(
                self.item_count / self.elapsed_time if self.elapsed_time > 0 else -1.0
            ).quantize(Decimal(".01"), rounding=ROUND_HALF_UP),
        )

    def add_time(self, other):
        elapsed_time = self.elapsed_time + other.elapsed_time
        item_count = self.item_count
        return TraceInterval(elapsed_time, item_count)

    def sub_time(self, other):
        elapsed_time = self.elapsed_time - other.elapsed_time
        item_count = self.item_count
        return TraceInterval(elapsed_time, item_count)

    def freeze(self):
        self.frozen = True
        return self


class TraceCounter:
    def __init__(self, time_period, item_samples=0):
        self.start = timer()
        self.frozen = False
        self.interval = TraceInterval()
        self.time_period = time_period
        self.item_samples = item_samples

    def update(self, item_delta=1):
        elapsed = self.start.elapsed()
        item_count = self.interval.item_count + item_delta
        self.interval = TraceInterval(elapsed, item_count)
        return self.is_expired()

    def flush(self):
        self.update(item_delta=0)
        return self.interval

    def is_expired(self):
        elapsed = self.start.elapsed()
        item_count = self.interval.item_count
        return (self.time_period == 0 or elapsed >= self.time_period) or (
            self.item_samples > 0 and item_count >= self.item_samples
        )

    def freeze(self):
        self.flush().freeze()
        self.frozen = True
        return self

    def __str__(self):
        return str(self.interval)

    def to_dict(self):
        return self.interval.to_dict()


class TraceFrame:
    def __init__(
        self, name, owner, parent, ctx, logger, time_period, item_samples, verbose
    ):
        self.start = timer()
        self.name = name
        self.owner = owner
        self.parent = parent
        self.logger = logger
        self.ctx = dict(ctx)

        self.time_period = time_period
        self.item_samples = item_samples
        self.verbose = verbose

        self.frozen = False
        self.total = self.make_interval()
        self.callee = self.make_interval()
        self.counter = self.make_counter(
            time_period=self.time_period, item_samples=self.item_samples
        )

    @classmethod
    def make_interval(cls):
        return TraceInterval()

    @classmethod
    def make_counter(cls, time_period, item_samples=0):
        return TraceCounter(time_period=time_period, item_samples=item_samples)

    def root_frame(self):
        o = self
        if o.parent is None:
            return o
        else:
            return o.parent.root_frame()

    def uptime(self):
        return self.owner.start.elapsed()

    def open(self):
        self.reload()
        if self.verbose > 0:
            self.report_open()
        return self

    def close(self):
        self.reload()
        if self.verbose > 0:
            self.report_close()
        return self

    def reload(self):
        self.counter = self.make_counter(
            time_period=self.time_period, item_samples=self.item_samples
        )

    def flush(self):
        self.aggregate(no_report=True)
        return self

    def freeze(self):
        self.flush()
        self.frozen = True
        return self

    def net_interval(self):
        return self.total.sub_time(self.callee)

    def aggregate(self, no_report=False):
        self.total = self.total + self.counter.flush()
        if not no_report:
            self.report_sample()
        self.reload()

    def update(self, item_delta=1):
        expired = self.counter.update(item_delta=item_delta)
        if expired:
            self.aggregate()

    def accumulate(self, frame):
        callee_total = frame.freeze().total
        self.callee = self.callee.add_time(callee_total)
        self.flush()
        frame.report_subtotal(self.total)
        return self.total

    def disabled(self):
        return not self.logger.isEnabledFor(logging.DEBUG)

    def log_prefix(self, what, no_rec=False, is_tot=False, outer_total=None):
        """
        to transform log to json:

        ```

        ( \
            echo '['; \
            python tests/dve_tests/common/util/test_trace.py |& \
            grep -v '__main__'  | \
            cut -f2- | \
            grep '^\{' ; \
            echo ' {} ]' \
        ) | \
        jq '.'

        ```

        to project some column:

        ```

        ( \
            echo '['; \
            python tests/dve_tests/common/util/test_trace.py |& \
            grep -v '__main__'  | \
            grep '"tag": {"s": "._3_", "w": "+"}' | \
            cut -f2,4,8,9,10 | \
            grep '^\{' ; \
            echo ' {} ]' \
        ) | \
        jq '.'


        ```


        """
        row = dict(
            ts={},
            tag={},
            rec={},
            sum={},
            tot={},
            net={},
            ctx={},
        )

        row["ts"] = dict(
            t=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ms=int(self.uptime() * 1000),
        )

        row["tag"] = dict(s=self.name, w=what)

        row["ctx"] = self.ctx

        if not no_rec:
            row["rec"] = self.counter.to_dict()

        if not no_rec or is_tot:
            row["sum"] = self.total.to_dict()

        if is_tot:
            row["net"] = self.net_interval().to_dict()

        if is_tot:
            row["tot"] = outer_total.to_dict()

        return to_json_oneline(
            f"""\
        \t{{
          \t"ts": {row['ts']},
          \t"rec": {row['rec']},
          \t"sum": {row['sum']},
          \t"net": {row['net']},
          \t"tot": {row['tot']},
          \t"tag": {row['tag']}
        \t}}
        \t,\t
        """
        )

    def report_open(self):
        if self.disabled():
            return
        prefix = self.log_prefix(">", no_rec=False)
        text = f"{prefix}"
        self.logger.debug(text)

    def report_close(self):
        if self.disabled():
            return
        prefix = self.log_prefix("<", no_rec=False)
        text = f"{prefix}"
        self.logger.debug(text)

    def report_sample(self):
        if self.disabled():
            return
        prefix = self.log_prefix("+")
        text = f"{prefix}"
        self.logger.debug(text)

    def report_subtotal(self, parent_total):
        if self.disabled():
            return
        prefix = self.log_prefix(
            "#", no_rec=True, is_tot=True, outer_total=parent_total
        )
        text = f"{prefix}"
        self.logger.debug(text)


class TraceLogger:
    def __init__(self, name="_", time_period=30, item_samples=0, verbose=0):
        self.start = timer()
        self.name = name
        self.time_period = time_period
        self.item_samples = item_samples
        self.verbose = verbose

        self.logger = logging.getLogger("TRACE" + "." + self.name)

        self.frames = []
        self.top = None
        self.root = self.push_frame(self.name + "._0_")

    @classmethod
    def make_frame(
        cls, name, owner, parent, ctx, logger, time_period, item_samples, verbose
    ):
        return TraceFrame(
            name, owner, parent, ctx, logger, time_period, item_samples, verbose
        )

    def push_frame(self, name):
        ctx = {} if self.top is None else self.top.ctx
        result = self.make_frame(
            name,
            owner=self,
            parent=self.top,
            ctx=ctx,
            logger=self.logger,
            time_period=self.time_period,
            item_samples=self.item_samples,
            verbose=self.verbose,
        )
        self.frames.append(result)
        self.top = self.frames[-1]
        return result

    def pop_frame(self):
        result = self.frames.pop()
        self.top = self.frames[-1]
        return result

    def enter(self, name=None):
        if name is None:
            name = f"._{len(self.frames)}_"
            # name = self.name+f"._{len(self.frames)}_"
        self.push_frame(name=name).open()

    def exit(self):
        frame = self.pop_frame()
        self.top.accumulate(frame)
        return frame.close()

    def __enter__(self):
        self.enter()

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.exit()

    def ctx(self):
        return self.top.ctx

    def all(self):
        self.top.counter.time_period = 0
        return self

    def update(self, item_delta=1):
        return self.top.update(item_delta=item_delta)


def trace_logger(name="_", time_period=30, item_samples=0, verbose=0):
    result = TraceLogger(
        name, time_period=time_period, item_samples=item_samples, verbose=verbose
    )
    return result
