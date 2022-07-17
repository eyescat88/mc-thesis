import sys
import logging
# from subprocess import Popen, PIPE, STDOUT, call, run
from subprocess import run
from shlex import join
from textwrap import dedent
from collections import namedtuple

# import dve.cli as cli
import dve.scripts.runner as runner

import dve.common.util.time as tm
import dve.common.util.file as fu

from dve.config.data import DATA_WORK
# from dve.config.data import DATA_LOGS
# from dve.config.data import DATA_HOME
# from dve.config.data import DATA_HOST
# from dve.config.data import DATA_TEMP
# from dve.config.data import DATA_TEST
# from dve.config.data import DATA_USER
# from dve.config.data import DATA_DESK

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////


def parm(job: str, group: str, filename: str):
    return dict(job=job, group=group, filename=filename)


def to_parms(parms):
    result = dict()
    for parm in parms:
        result[parm["job"]] = parm
    if parms:
        result["auto"] = parms[0]
    return result


# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////

X_SCRIPT = "finbert_x.py"


DD_PARMS = to_parms(
    [
        parm("xxxx", "tesla", "Tesla 17 Caratteri Strani 2019 01 30   2018 12 31 .csv"),
    ]
)

# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////

X_ARCH = "H16"  # @TODO: arch getenv

MpConf = namedtuple("MpConf", ["enable", "cores", "gpus", "slots"])

X_MP_CONF = dict(
    H8=MpConf(
        enable=False,
        cores=8,
        gpus=0,
        slots=1,
    ),
    H16=MpConf(
        enable=True,
        cores=16,
        gpus=0,
        slots=2,
    ),
    NC6=MpConf(
        enable=False,
        cores=6,
        gpus=1,
        slots=1,
    ),
)


def mp_conf(parm=None, name=None, args=None, argv=None):
    return X_MP_CONF[X_ARCH]


# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////

proc_num = 0
init_timer = tm.timer()


def new_proc_id():
    global proc_num
    proc_num = proc_num + 1
    return proc_num


def to_oneline(command_line):
    return dedent(command_line).replace("\n", " ").replace("; ", ";")


def to_manylines(command_lines):
    return dedent(command_lines)


def run_context(command, parm, name, args, argv=None):
    conf = mp_conf(parm=parm, name=name, args=args, argv=argv)
    proc_id = new_proc_id()
    timer = tm.timer()
    prefix = f"//run({proc_id},{init_timer}):"
    ctx = dict(
        command=command,
        proc_id=proc_id,
        timer=timer,
        prefix=prefix,
        mp_conf=conf,
        parm=parm,
        name=name,
        args=args,
        argv=argv,
    )
    return ctx


def run_proc(ctx, command):
    command_line = command
    log.info(f"* {ctx['prefix']} {command_line}")
    rp = run(command_line, shell=True, check=True)
    rc = rp.returncode
    return rc


def run_para_imm(ctx, command):
    mp_conf = ctx["mp_conf"]
    command_line = f"""\
    (
    :
    ; export X_NUMA_SLOTS="${{X_NUMA_SLOTS:=$(numactl -s | grep ^cpubind | cut -d: -f2)}}"
    ; export X_NUMA_CORES="${{X_NUMA_CORES:=$(lscpu | grep 'Core\\(s\\) per socket:' | cut -d: -f2 | tr -d ' ')}}"
    ; export X_CORE_JOBID="${{X_CORE_JOBID:=$(date -Isec)-$$}}"

    ; echo "### $(date -Isec) - $(date +%s) -- #job:[$X_CORE_JOBID] >>"

    ; env  X_CORE_MODE=1 "{command}"

    ; parallel
       env
        OMP_NUM_THREADS=${{OMP_NUM_THREADS:=$X_NUMA_CORES}}
        GOMP_CPU_AFFINITY={{}}
        X_CORE_SLOT={{}} X_CORE_SLOTS="$(echo $X_NUMA_SLOTS | wc -w)"
        X_CORE_MODE=0

       numactl
          --cpunodebind={{}}
          --membind={{}}

       "{command}"

    ::: $X_NUMA_SLOTS

    ; env  X_CORE_MODE=2 "{command}"

    ; echo "### $(date -Isec) - $(date +%s) -- #job:[$X_CORE_JOBID] <<"
    )
    """
    command_line = to_oneline(command_line)
    log.info(f"* {ctx['prefix']} {command_line}")
    rp = run(command_line, shell=True, check=True)
    rc = rp.returncode
    return rc


def run_para(ctx, command):
    mp_conf = ctx["mp_conf"]
    script_body = f"""\
    #!/bin/sh

    ##
    # run (parallel): {command}
    #

    set -x

    export X_NUMA_SLOTS="${{X_NUMA_SLOTS:=$(numactl -s | grep ^cpubind | cut -d: -f2)}}"
    export X_NUMA_CORES="${{X_NUMA_CORES:=$(lscpu | grep 'Core\\(s\\) per socket:' | cut -d: -f2 | tr -d ' ')}}"
    export X_CORE_JOBID="${{X_CORE_JOBID:=$(date -Isec)-$$}}"

    echo "### $(date -Isec) - $(date +%s) -- #job:[$X_CORE_JOBID] >>"

    env  X_CORE_MODE=1 {command}

    parallel  \
       env \
        OMP_NUM_THREADS=${{OMP_NUM_THREADS:=$X_NUMA_CORES}} \
        GOMP_CPU_AFFINITY={{}} \
        X_CORE_SLOT={{}} X_CORE_SLOTS="$(echo $X_NUMA_SLOTS | wc -w)" \
        X_CORE_MODE=0 \
          \
       numactl \
          --cpunodebind={{}} \
          --membind={{}} \
       \
       '{command}' \
       \
    ::: $X_NUMA_SLOTS

    env  X_CORE_MODE=2 {command}

    echo "### $(date -Isec) - $(date +%s) -- #job:[$X_CORE_JOBID] <<"

    """
    script_body = to_manylines(script_body)
    script_file = fu.write_script(script_body)
    script_out = fu.replace_ext(script_file, ".out")
    script_command = f"/bin/bash -c {script_file} 2>&1 | tee -a {script_out} "
    log.info(f"* {ctx['prefix']} {script_command} # {command}")
    rp = run(script_command, shell=True, check=True)
    rc = rp.returncode
    return rc


def run_command(command, parm, name, args, argv=None):
    ctx = run_context(command=command, parm=parm, name=name, args=args, argv=argv)
    log.info(f"> {ctx['prefix']} {command}")
    if ctx["mp_conf"].enable:
        rc = run_para(ctx, command)
    else:
        rc = run_proc(ctx, command)
    log.info(f"< {ctx['prefix']}  (rc:{rc},elapsed{ctx['timer']})")
    return rc


# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////


def cmd_args(parm, name, args, argv=None):
    result = [
        "--jobname",
        parm["job"],
        "--group",
        parm["group"],
        "--filename",
        parm["filename"],
    ]
    s = join(result)
    return s


def cmd_script(parm, name, args, argv=None):
    result = f"python {X_SCRIPT} {cmd_args(parm,name,args,argv)}"
    return result


def call_command(command, name, args, argv=None):
    parm = dict()
    run_command(command, parm, name, args, argv)


def call_script(name, args, argv=None):
    parm = DD_PARMS[name]
    command = cmd_script(parm, name, args, argv)
    run_command(command, parm, name, args, argv)


# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////


def exec_auto(name, args, argv=None):
    call_script(name, args, argv)


def exec_tesla_001(name, args, argv=None):
    call_script(name, args, argv)


# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////


def exec_test_find(name, args, argv=None):
    call_command(
        to_oneline(
            f"""\
        find {DATA_WORK} -name '*.py' | xargs -l1 -I{{}} basename {{}}
    """
        ),
        name,
        args,
        argv,
    )


def exec_test_numa(name, args, argv=None):
    test_script = to_oneline(
        f"""\
        import os;
        import time;
        print({{}},
           os.getpid(),
           os.getenv(\\"X_CORE_SLOT\\"),
           os.getenv(\\"OMP_NUM_THREADS\\"));
        time.sleep(1);
    """
    )
    call_command(f"python -c '{test_script}'", name, args, argv)


def exec_test(name, args, argv=None):
    # exec_test_find(name, args, argv)
    exec_test_numa(name, args, argv)
    print("#<auto:test>:" + str(args))


# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////


def argparser(options=None):
    """Base Argument Parser."""
    parser = runner.argparser(options)

    parser.add_argument("-n", "--name", type=str, help="stage execute", default="_")
    return parser


def parse_args(argv=None):
    """Process command line arguments."""
    if not argv:
        argv = sys.argv[1:]

    parser = argparser()
    args = parser.parse_args(argv)
    return args


def exec(args, argv=None):
    """Dispatch execution to target entry point."""

    name = args.name
    if name == "_":
        name = "auto"

    if name == "auto":
        RC = exec_auto(name, args, argv)
    elif name == "d_tesla_001":
        RC = exec_tesla_001(name, args, argv)
    elif name == "test":
        RC = exec_test(name, args, argv)
    else:
        raise ValueError(f"invalid spec: {name}!")
    return RC


def main(argv=None):
    """Process command line arguments."""
    print(__name__ + "main:" + str(argv))
    log.info(">> ### " + __name__ + ".main(argv=" + str(argv) + ")")
    args = parse_args(argv)
    RC = exec(args, argv)
    log.info("<< ###" + __name__ + ".main => (rc=" + str(RC) + ")")
    return RC


if __name__ == "__main__":
    main(sys.argv[1:])
