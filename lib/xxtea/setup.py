from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize(['xxtea_vars.pyx'],
                          annotate=True),
)