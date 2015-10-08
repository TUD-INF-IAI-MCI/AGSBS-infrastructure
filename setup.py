from distutils.core import setup
import sys, os
import shutil
sys.path.insert(0, '.') # MaGSBS must be from _this_ directory
import MAGSBS.config

# slightly fishy
packages = []
if 'win32' in sys.platform.lower() or 'wind' in sys.platform.lower():
    scripts = [os.path.join('cli','matuc.py')]
    modules = ["MAGSBS"]
else:
    # on UNIX, we want a nice shell script ;)
    sys.path.append('cli')
    scripts = [os.path.join('bin', 'matuc')],
    packages = ['MAGSBS']
    modules = ['matuc']

# install MAGSBS-module

setup(name='MAGSBS',
      version=MAGSBS.config.VERSION,
      packages=packages,
      py_modules=modules
      )

# matuc distribution:
os.chdir('cli')
setup(name='MAGSBS/matuc',
      version=MAGSBS.config.VERSION,
      py_modules = modules,
      scripts=scripts
      )


# optional clean up
shutil.rmtree('build')
os.chdir('..')
shutil.rmtree('build')
