#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""Smartly install local python source packages."""


import os
import re
import sys
import tarfile

__program__ = 'installdist'
__version__ = '0.1.2'


class Installer:
    """A pip-like wrapper for managing package un/installation."""

    def __init__(self):
        self.options = None
        self.suffixes = ['-rev', '.rev', '-dev', '.dev',
                         '-beta', '.beta', '-alpha', '.alpha']

    def checkpip(self):
        """Raise exception if the desired version of pip is not available."""

        def finder(script):
            """Raise exception upon failure to find executable."""
            try:
                from distutil.spawn import find_executable
            except ImportError:
                from shutil import which as find_executable

            if not find_executable(script):
                raise FileNotFoundError("'{0}' not available".format(script))

        if self.options.pip2:
            finder('pip2')
        else:
            finder('pip3')

    def detectdistpath(self, startpath):  # pylint: disable=R0201
        """Return the relative path to the desired 'dist/' directory."""

        searchpaths = ['.', 'dist/', '../dist/']

        for searchpath in searchpaths:
            testpath = os.path.join(startpath, searchpath) if startpath else \
                       searchpath
            basename = os.path.basename(os.path.abspath(testpath))
            if os.path.isdir(testpath) and basename == 'dist':
                return testpath

    def findname(self, packagepath):  # pylint: disable=R0201
        """
        Return an approximated package name.

        i.e. /path/to/archive-0.3.tar.gz ==> archive
        """

        if packagepath.endswith('.tar.gz'):
            try:
                tfo = tarfile.open(packagepath)
                pkgfile = tfo.extractfile(os.path.join(tfo.getnames()[0], 'PKG-INFO'))
                pkginfo = pkgfile.read().decode()

                match = re.search(r'(?<=Name: ).+', pkginfo)
                if match:
                    return match.group()

            except:
                pass

        return os.path.basename(packagepath).split('-')[0]

    def findpackage(self, distpath):
        """
        Scan files in the 'dist/' directory and return the path
        to the desired package archive.
        """

        import glob

        # couldn't locate dist path (assume pkg/s are in the current directory)
        if distpath is None:
            distpath = '.'

        extension = 'whl' if self.options.wheel else 'tar.gz'
        directory = os.path.join(distpath, '*.' + extension)
        paths = glob.glob(directory)
        files = [f for f in paths if os.path.isfile(f) and os.access(f, os.R_OK)]

        if files:
            # select the most recent file
            if self.options.newsort:
                return max(files, key=os.path.getctime)
            # select the highest version identified via max()
            else:
                def versionkey(path):
                    return os.path.basename(path).rstrip('.' + extension).split('-')[1]

                maxfile = max(files, key=versionkey)

                dirname = os.path.dirname(maxfile)
                basename = os.path.basename(maxfile)
                filename = basename.rstrip('.' + extension)

                # check for packages with developmental versions
                for suffix in self.suffixes:
                    basename = filename + suffix + '.' + extension
                    testfile = os.path.join(dirname, basename)
                    if os.path.isfile(testfile):
                        return testfile

                return maxfile

    def installpackage(self, packagepath):
        """Install package archive with pip."""

        _execute(self.options.pipv, 'install', '--user', packagepath)

    # def installpackage(self, packagepath):
    #     """Install package archive with pip."""

    #     from pip.commands.install import InstallCommand
    #     install = InstallCommand()
    #     install.main(['--user', packagepath])

    def main(self, args=None):
        """Start package un/installation process."""

        self.options = _parser(args)

        if self.options.pip2:
            self.options.pipv = 'pip2'
        else:
            self.options.pipv = 'pip3'

        self.checkpip()

        distpath = self.detectdistpath(self.options.package)
        packagepath = self.findpackage(distpath)

        if not packagepath:
            _fatal("Unable to find a package to install")

        packagename = self.findname(packagepath)

        if packagename:
            self.promptuninstall(packagename)

        self.promptinstall(packagepath)

    def promptinstall(self, packagepath):
        """Prompt to install package archive."""

        print("\nAre you sure you'd like to install the following package (y/n)?")
        print(os.path.abspath(packagepath))
        if _confirm():
            if self.options.dryrun:
                print("DRYRUN: Installing '{0}'".format(packagepath))
            else:
                self.installpackage(packagepath)
        else:
            sys.exit(1)

    def promptuninstall(self, packagename):
        """Prompt to uninstall package archive."""

        results = self.showpackage(packagename)

        if results:
            print('Name:', results['name'])
            print('Version:', results['version'])
            print('Location:', results['location'])
            print()
            prompt = "Are you sure you'd like to uninstall {0} {1} (y/n)? " \
                     .format(packagename, results['version'])
            if _confirm(prompt):
                if self.options.dryrun:
                    print("DRYRUN: Uninstalling {0} {1}"
                          .format(packagename, results['version']))
                else:
                    self.uninstallpackage(packagename)
            else:
                sys.exit(1)

    def showpackage(self, packagename):
        """Return a set of details for an installed package."""

        import subprocess

        process = subprocess.Popen([self.options.pipv, 'show', packagename],
                                   stderr=subprocess.PIPE,
                                   stdout=subprocess.PIPE)

        info = process.stdout.read().decode().splitlines()[1:]

        results = {}

        if info:
            results['name'] = info[0].split()[1]
            results['version'] = info[1].split()[1]
            results['location'] = info[2].split()[1]

        return results

    # def showpackage(self, packagename):
    #     """Return a set of details for an installed package."""

    #     from pip.commands.show import search_packages_info

    #     try:
    #         generator = search_packages_info([packagename])
    #         return list(generator)[0]
    #     except:
    #         return

    def uninstallpackage(self, packagename):
        """Uninstall package archive with pip."""

        _execute(self.options.pipv, 'uninstall', packagename)

    # def uninstallpackage(self, packagename):
    #     """Uninstall package archive with pip."""

        # pip module sometimes fails to identify package to be uninstalled
        # from pip.commands import UninstallCommand
        # uninstall = UninstallCommand()
        # uninstall.main([packagename])


def _confirm(prompt=None):
    """Request confirmation from the user."""

    rawinput = input() if prompt is None else input(prompt)

    try:
        return True if rawinput[0].lower() == 'y' else False
    except IndexError:
        return False


def _error(*args):
    """Print error message to stderr."""
    print('ERROR:', *args, file=sys.stderr)  # pylint: disable=W0142


def _execute(*args):
    """Execute shell commands with access to terminal."""
    os.system(' '.join(args))


def _fatal(*args):
    """Print error message to stderr then exit."""
    _error(*args)
    sys.exit(1)


def _parser(args):
    """Parse command-line options and arguments. Arguments may consist of any
    combination of directories, files, and options."""

    import argparse

    parser = argparse.ArgumentParser(
        add_help=False,
        description="Install a local python source package.",
        epilog="NOTE: By default, %(prog)s uninstalls any preexisting "
               "installation then installs the highest version tarball "
               "available via pip3",
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
        "-h", "--help",
        action="help",
        help=argparse.SUPPRESS)
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
        "--version",
        action="version",
        version="{0} {1}".format(__program__, __version__))
    parser.add_argument(
        action="append",
        dest="targets",
        help=argparse.SUPPRESS,
        nargs="*")

    return parser.parse_args(args)


def main():
    """Start application."""
    installer = Installer()
    installer.main()


if __name__ == '__main__':
    main()
