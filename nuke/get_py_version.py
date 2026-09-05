import sys


def write_py_version(path: str) -> None:
    with open(path, "w") as f:
        f.write(f"{sys.version_info.major}.{sys.version_info.minor}")


if __name__ == "__main__":
    write_py_version(sys.argv[1])
