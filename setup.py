from distutils.core import setup
import distutils.command.install_scripts
import MAGSBS
import os
import shutil, sys

class my_install(distutils.command.install_scripts.install_scripts):
    """Custom script installer. Stript .py extension if not on Windows."""
    def run(self):
        distutils.command.install_scripts.install_scripts.run(self)
        for script in self.get_outputs():
            if script.endswith(".py") and not ('wind' in sys.platform or 'win32'
                    in sys.platform):
                # strip file ending (if not on windows) to make it executable as
                # a command
                shutil.move(script, script.rstrip('.py'))

# before anything, set umask, if possible (will be ignored on Windows). Most
# users nowadays use sudo and that does not pass the umask along. Hence some
# users end up with an installed module which they don't have permissions to
# read from.
os.umask(0o22) # everybody can read, only owner can write

setup(name='MAGSBS-matuc',
      version=str(MAGSBS.config.VERSION),
      packages=['MAGSBS', 'MAGSBS.quality_assurance', 'matuc_impl'],
      scripts=["matuc.py", "matuc_js.py"],
      cmdclass = {"install_scripts": my_install}
    )

# optional clean up
if os.path.exists('build'):
    shutil.rmtree('build')
