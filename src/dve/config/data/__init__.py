import os.path

import rootpath


def conf_dir(env_key, default_value):
    p = os.path.expanduser(os.getenv(env_key, default_value))
    return rootpath.detect(__file__, "^.git$") + p[1:] if p.startswith("./") else p


DATA_WORK = conf_dir("PC_DATA_HOME", "./.")

DATA_LOGS = conf_dir("PC_DATA_HOME", "./logs")

DATA_TEMP = conf_dir("PC_DATA_HOME", "./data/tmp")
DATA_TEST = conf_dir("PC_DATA_HOME", "./data/int/test")

DATA_HOME = conf_dir("PC_DATA_HOME", "./data/ext/home")
DATA_HOST = conf_dir("PC_DATA_HOST", "./data/ext/host")
DATA_USER = conf_dir("PC_DATA_USER", "./data/ext/user")

DATA_DESK = conf_dir("PC_DATA_DESK", "~/Desktop")
