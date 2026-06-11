import runpy, pathlib

runpy.run_path(str(pathlib.Path(__file__).parent / "src" / "dashboard.py"), run_name="__main__")
