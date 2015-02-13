#!/usr/bin/python3
"""Smartly install local python source packages."""


__program__ = 'subsystem'
__version__ = '0.3'


# --- BEGIN CODE --- #

class Installer:
    def __init__(self):
        self.options = None

    def checkPip(self):
        """Raise an exception if the desired version of pip is not available."""

        def finder(script):
            """Raise an exception upon failure to find executable."""
            try:
                from distutil.spawn import find_executable
            except ImportError:
                from shutil import which as find_executable

            if not find_executable(script):
                raise FileNotFoundError("'%s' is not available" % script)

        if self.options.pip2:
            # import sys
            # sys.tracebacklimit = 1
            try:
                raise NotImplementedError("'--pip2' is not yet implemented")
            except NotImplementedError as exc:
                print_exception(exc)
            finder('pip2')
        else:
            finder('pip3')

    def detectDistPath(self, startpath):
        """Return the relative path to the desired 'dist/' directory."""

        import os

        searchpaths = ['.', 'dist/', '../dist/']

        for searchpath in searchpaths:
            testpath = os.path.join(startpath, searchpath) if startpath else searchpath
            basename = os.path.basename(os.path.abspath(testpath))
            if os.path.isdir(testpath) and basename == 'dist':
                return testpath

    def findName(self, packagepath):
        """
        Return an approximated package name.

        i.e. /path/to/archive-0.3.tar.gz ==> archive
        """

        import os
        return os.path.basename(packagepath).split('.')[0].split('-')[:-1][0]

    def findPackage(self, distpath):
        """
        Scan files in the 'dist/' directory and return the path
        to the desired package archive.
        """

        import glob
        import os

        extension = 'whl' if self.options.wheel else 'tar.gz'
        directory = os.path.join(distpath, '*.' + extension)
        paths = glob.glob(directory)
        files = [f for f in paths if os.path.isfile(f) and os.access(f, os.R_OK)]

        if files:
            if self.options.newsort:
                return max(files, key=os.path.getctime)
            else:
                return max(files)

    def installPackage(self, packagepath):
        """Install package archive with pip."""

        from pip.commands.install import InstallCommand

        install = InstallCommand()
        install.main(['--user', packagepath])

    def main(self, options):
        self.options = parse()

        self.checkPip()

        distpath = self.detectDistPath(options.package)
        packagepath = self.findPackage(distpath)

        packagename = self.findName(packagepath)

        if packagename:
            self.promptUninstall(packagename)

        self.promptInstall(packagepath)

    def promptInstall(self, packagepath):
        """Prompt to install package archive."""

        import sys
        from os.path import abspath

        print("PACKAGE PATH:", abspath(packagepath))
        prompt = "Are you sure you'd like to install '%s'? " % packagepath
        response = getch(prompt).lower()
        print()
        if response == 'y':
            if self.options.dryrun:
                print('DRYRUN: running installPackage()...')
            else:
                self.installPackage(packagepath)
        else:
            sys.exit(1)

    def promptUninstall(self, packagename):
        """Prompt to uninstall package archive."""

        results = self.showPackage(packagename) 

        if results:
            import sys
            print('Name:', results['name'])
            print('Version:', results['version'])
            print('Location:', results['location'])
            print('---' * 3)
            prompt = "Are you sure you'd like to uninstall '%s'? " % results['name']
            response = getch(prompt).lower()
            print()
            if response == 'y':
                if self.options.dryrun:
                    print('DRYRUN: running uninstallPackage()...')
                else:
                    self.uninstallPackage(packagename)
            else:
                sys.exit(1)

    def showPackage(self, packagename):
        """Return a set of details for an installed package."""

        from pip.commands.show import search_packages_info

        try:
            generator = search_packages_info([packagename])
            return list(generator)[0]
        except:
            return

    def uninstallPackage(self, packagename):
        """Uninstall package archive with pip."""

        from pip.commands import UninstallCommand

        uninstall = UninstallCommand()
        uninstall.main([packagename])


def getch(prompt=None):
    """Request a single character input from the user."""
    import sys

    if prompt:
        sys.stdout.write(prompt + ' ')
        sys.stdout.flush()

    if sys.platform in ['darwin', 'linux']:
        import termios
        import tty
        file_descriptor = sys.stdin.fileno()
        settings = termios.tcgetattr(file_descriptor)
        try:
            tty.setraw(file_descriptor)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(file_descriptor, termios.TCSADRAIN, settings)
    elif sys.platform in ['cygwin', 'win32']:
        import msvcrt
        return msvcrt.getwch()


def main():
    options = parse()

    installer = Installer()
    installer.main(options)


def parse():
    """Parse command-line options and arguments. Arguments may consist of any
    combination of directories, files, and options."""

    import argparse

    parser = argparse.ArgumentParser(
        add_help=False,
        description="Install a local python source package.",
        epilog="NOTE: By default, %(prog)s uninstalls any preexisting installation then installs the highest version tarball available via pip3",
        usage="%(prog)s [OPTIONS] FILES/FOLDERS")
    parser.add_argument(
        "-2", "--pip2",
        action="store_true",
        dest="pip2",
        help="install package with pip2")
    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        dest="dryrun",
        help="indicate the commands to be run but do not execute them")
    parser.add_argument(
        "-n", "--new",
        action="store_true",
        dest="newsort",
        help="install package possessing the most recent timestamp")
    parser.add_argument(
        "-p", "--package",
        action="store",
        default=".",
        dest="package",
        help="install package by directory name (from a parent directory)")
    parser.add_argument(
        "-w", "--wheel",
        action="store_true",
        dest="wheel",
        help="install wheel package")
    parser.add_argument(
        "-h", "--help",
        action="help",
        help=argparse.SUPPRESS)
    parser.add_argument(
        "--version",
        action="version",
        version="%s %s" % (__program__, __version__))
    parser.add_argument(
        action="append",
        dest="targets",
        help=argparse.SUPPRESS,
        nargs="*")

    return parser.parse_args()


def print_exception(exception):
    """Print fatal exception as briefly as possible, then exit."""

    import sys
    print('%s: %s' % (exception.__class__.__name__, exception.args[0]))
    sys.exit(1)


if __name__ == '__main__':
    main()
