import subprocess

def run_tests():
    subprocess.call(["pytest", "-q", "--alluredir=./report"], shell=True)


if __name__ == "__main__":
    run_tests()
