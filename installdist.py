#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""Smartly install local python source packages."""


import logging
import os
import sys
import tarfile
import zipfile

__program__ = 'installdist'
__version__ = '0.1.5'


class Installer:
    """A pip-like wrapper for managing package un/installation."""

    def __init__(self):
        self.options = None

    def checkpip(self):
        """Configure pip and verify that the desired version is available."""

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
            self.options.pipv = 'pip2'
        else:
            finder('pip3')
            self.options.pipv = 'pip3'

        LOGGER.info("Configured to install packages with: '%s'", self.options.pipv)

    def configpackage(self):
        """Determine what package is to be installed and from where."""

        # convert list to string (i.e. [None] ==> None)
        self.options.target = self.options.target[0]

        pkgpath = None

        if self.options.target is not None:
            LOGGER.info("Configured to install target package: '%s'", self.options.target)
            if os.path.isfile(self.options.target):
                pkgpath = self.options.target
        else:
            LOGGER.info("Configured to scan parent directory: '%s'", self.options.package)
            distpath = detectdistpath(self.options.package)
            pkgpath = self.findpackage(distpath)

        if pkgpath:
            LOGGER.info("Configured pkgpath to: '%s'", pkgpath)
            return pkgpath
        else:
            _fatal('Unable to determine package to install')

    def findpackage(self, distpath):
        """
        Scan files in the 'dist/' directory and return the path
        to the desired package archive.
        """

        def versionkey(pkgpath):
            """Return the version of package (to be used as a sort function)."""

            wrapper = str

            try:
                # attempt to use version object (able to perform comparisons)
                from distutils.version import LooseVersion as wrapper
            except ImportError:
                pass

            return wrapper(self.getmetafield(pkgpath, 'version'))

        import glob

        # couldn't locate dist path (assume pkg/s are in the current directory)
        if distpath is None:
            distpath = '.'

        extension = '.whl' if self.options.wheel else '.tar.gz'
        directory = os.path.join(distpath, '*' + extension)
        paths = glob.glob(directory)
        files = [f for f in paths if os.path.isfile(f) and os.access(f, os.R_OK)]

        if files:
            if self.options.newsort:
                # select the package with the most recently changed timestamp
                return max(files, key=os.path.getctime)
            else:
                # select the package with the highest version number
                return max(files, key=versionkey)

    def getmetapath(self, afo, pkgpath):
        """
        Return path to the metadata file within a tarfile or zipfile object.

        tarfile: PKG-INFO
        zipfile: metadata.json
        """

        if isinstance(afo, tarfile.TarFile):
            pkgname = afo.fileobj.name
            for path in afo.getnames():
                if path.endswith('/PKG-INFO'):
                    return path
        elif isinstance(afo, zipfile.ZipFile):
            pkgname = afo.filename
            for path in afo.namelist():
                if path.endswith('.dist-info/metadata.json'):
                    return path

        raise AttributeError("Unable to identify metadata file for '{0}'" \
                             .format(os.path.basename(pkgname)))

    def getmetafield(self, pkgpath, field):
        """
        Return the value of a field from package metadata file.
        Whenever possible, version fields are returned as a version object.

        i.e. getmetafield('/path/to/archive-0.3.tar.gz', 'name') ==> 'archive'
        """

        # package is a tar archive
        if pkgpath.endswith('.tar.gz'):

            with tarfile.open(pkgpath) as tfo:
                with tfo.extractfile(self.getmetapath(tfo, pkgpath)) as mfo:
                    metalines = mfo.read().decode().splitlines()

            for line in metalines:
                if line.startswith(field.capitalize() + ': '):
                    return line.split(': ')[-1]

        # package is a wheel (zip) archive
        elif pkgpath.endswith('.whl'):

            import json

            with zipfile.ZipFile(pkgpath) as zfo:
                metadata = json.loads(zfo.read(self.getmetapath(zfo, pkgpath)).decode())
                try:
                    return metadata[field.lower()]
                except KeyError:
                    pass

        raise Exception("Unable to extract field '{0}' from package '{1}'". \
                        format(field, pkgpath))

    def installpackage(self, pkgpath):
        """Install package archive with pip."""

        args = [self.options.pipv, 'install', '--user', pkgpath]

        # install to system
        if self.options.system:
            args.remove('--user')

        LOGGER.info('Installing %s %s', self.pkgname, self.pkgversion)
        LOGGER.info(args)

        if self.options.dryrun:
            print("DRYRUN: Installing '{0}'".format(pkgpath))
            print(*args)
        else:
            _execute(*args)

    # def installpackage(self, pkgpath):
    #     """Install package archive with pip."""

    #     if self.options.dryrun:
    #         print("DRYRUN: Installing '{0}'".format(pkgpath))
    #     else:
    #         from pip.commands.install import InstallCommand
    #         install = InstallCommand()
    #         install.main(['--user', pkgpath])

    def main(self, args=None):
        """Start package un/installation process."""

        self.options = _parser(args)

        level = logging.INFO if self.options.verbose else logging.WARNING
        LOGGER.setLevel(level)

        self.checkpip()

        # determine the path of package that is to be (un)installed
        self.pkgpath = self.configpackage()

        # determine the name and version of the package from the archive's metadata
        self.pkgname = self.getmetafield(self.pkgpath, 'name')
        self.pkgversion = self.getmetafield(self.pkgpath, 'version')

        if self.pkgname:
            LOGGER.info("Identified package archive metadata: %s",
                        ' '.join([self.pkgname, self.pkgversion]))
            self.promptuninstall(self.pkgname)
        else:
            LOGGER.warning("Failed to identify package metadata")

        self.promptinstall(self.pkgpath)

    def promptinstall(self, pkgpath):
        """Prompt to install package archive."""

        prompt = "\n{0}\nAre you sure you'd like to install the aforementio" \
                 "ned package (y/N)? ".format(os.path.abspath(pkgpath))

        if _confirm(prompt):
            self.installpackage(pkgpath)
        else:
            sys.exit(1)

    # def promptinstall(self, pkgpath):
    #     """Prompt to install package archive."""

    #     print()
    #     print(os.path.abspath(pkgpath))

    #     prompt = "Are you sure you'd like to install the aforementioned " \
    #              "package (y/N)? "

    #     if _confirm(prompt):
    #         self.installpackage(pkgpath)
    #     else:
    #         sys.exit(1)

    def promptuninstall(self, pkgname):
        """Prompt to uninstall package archive."""

        results = self.showpackage(pkgname)

        if results:
            LOGGER.info("Identified installed package: '%s'", pkgname)

            print('Name:', results['name'])
            print('Version:', results['version'])
            print('Location:', results['location'])
            print()

            prompt = "Are you sure you'd like to uninstall {0} {1} (y/N)? " \
                     .format(pkgname, results['version'])

            if _confirm(prompt):
                self.uninstallpackage(pkgname, results['version'])
            else:
                sys.exit(1)

        else:
            LOGGER.info("Failed to identify any installed package: '%s'", pkgname)

    def showpackage(self, pkgname):
        """Return a set of details for an installed package."""

        import subprocess

        awk = "awk '/^Name: / {n=$2} /^Version: / {v=$2} /^Location: / {l=" \
              "$2} END{if (n==\"\") exit 1; printf \"%s|%s|%s\", n, v, l}'"

        process = subprocess.Popen(
            '{0} show {1} | {2}'.format(self.options.pipv, pkgname, awk),
            executable='bash',
            shell=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE)

        # check for a non-zero return code
        if process.wait(timeout=5) != 0:
            return False

        info = process.stdout.read().decode().split('|')

        results = {}

        if info:
            results['name'] = info[0]
            results['version'] = info[1]
            results['location'] = info[2]

        return results

    # def showpackage(self, pkgname):
    #     """Return a set of details for an installed package."""

    #     from pip.commands.show import search_packages_info

    #     try:
    #         generator = search_packages_info([pkgname])
    #         return list(generator)[0]
    #     except:
    #         pass

    def uninstallpackage(self, pkgname, pkgver):
        """Uninstall package archive with pip."""

        args = [self.options.pipv, 'uninstall', pkgname]

        LOGGER.info('Uninstalling %s %s', pkgname, pkgver)
        LOGGER.info(args)

        if self.options.dryrun:
            print('DRYRUN: Uninstalling {0} {1}'.format(pkgname, pkgver))
            print(*args)
        else:
            _execute(*args)

    # def uninstallpackage(self, pkgname, pkgver):
    #     """Uninstall package archive with pip."""

    #     if self.options.dryrun:
    #         print('DRYRUN: Uninstalling {0} {1}'.format(pkgname, pkgver))
    #     else:
    #         # WARNING: can fail to identify the package to be uninstalled
    #         from pip.commands import UninstallCommand
    #         uninstall = UninstallCommand()
    #         uninstall.main([pkgname])


def _confirm(prompt=None):
    """Request confirmation from the user."""

    rawinput = input() if prompt is None else input(prompt)

    try:
        return True if rawinput[0].lower() == 'y' else False
    except IndexError:
        return False


def _error(*args):
    """Print error message to stderr."""
    print('ERROR:', *args, file=sys.stderr)


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
        description='Install a local python source package.',
        epilog='NOTE: By default, %(prog)s uninstalls any pre-existing '
               'installation before reinstalling the highest version tarball '
               'available with pip3',
        usage='%(prog)s [OPTIONS] FILES/FOLDERS')
    parser.add_argument(
        '-2', '--pip2',
        action='store_true',
        dest='pip2',
        help='install package with pip2')
    parser.add_argument(
        '-d', '--dry-run',
        action='store_true',
        dest='dryrun',
        help='indicate the commands to be run but do not execute them')
    parser.add_argument(
        '-h', '--help',
        action='help',
        help=argparse.SUPPRESS)
    parser.add_argument(
        '-n', '--new',
        action='store_true',
        dest='newsort',
        help='install package possessing the most recent timestamp')
    parser.add_argument(
        '-p', '--package',
        action='store',
        default='.',
        dest='package',
        help='install package by parent directory')
    parser.add_argument(
        '-s', '--system',
        action='store_true',
        dest='system',
        help='install to system directory')
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        dest='verbose',
        help='set logging level to verbose')
    parser.add_argument(
        '--version',
        action='version',
        version='{0} {1}'.format(__program__, __version__))
    parser.add_argument(
        '-w', '--wheel',
        action='store_true',
        dest='wheel',
        help='install wheel package')
    parser.add_argument(
        action='append',
        dest='target',
        help=argparse.SUPPRESS,
        nargs='?')

    return parser.parse_args(args)


def detectdistpath(startpath):
    """Return the relative path to the desired 'dist/' directory."""

    searchpaths = ['.', 'dist/', '../dist/']

    for searchpath in searchpaths:
        testpath = os.path.join(startpath, searchpath) if startpath else \
                   searchpath
        basename = os.path.basename(os.path.abspath(testpath))
        if os.path.isdir(testpath) and basename == 'dist':
            return testpath


# def findname(pkgpath):
#     """
#     Return package name.

#     i.e. /path/to/archive-0.3.tar.gz ==> archive
#     """

#     metafile = 'PKG-INFO' if pkgpath.endswith('.tar.gz') else \
#                'METADATA' if pkgpath.endswith('.whl') else None

#     if metafile:
#         try:
#             with tarfile.open(pkgpath) as tfo:
#                 metapath = os.path.join(tfo.getnames()[0], metafile)
#                 with tfo.extractfile(metapath) as mfo:
#                     metalines = mfo.read().decode().splitlines()

#             for line in metalines:
#                 if line.startswith('Name: '):
#                     return line.split()[-1]

#         except:
#             pass

#     return os.path.basename(pkgpath).split('-')[0]


# def findversion(pkgpath):
#     """
#     Return package version.

#     i.e. /path/to/archive-0.3.tar.gz ==> 0.3
#     """

#     try:
#         # attempt to use version object (able to perform comparisons)
#         from distutils.version import LooseVersion as V
#     except ImportError:
#         # resort to a simple string object
#         V = str

#     metafile = 'PKG-INFO' if pkgpath.endswith('.tar.gz') else \
#                'METADATA' if pkgpath.endswith('.whl') else None

#     if metafile:
#         try:
#             with tarfile.open(pkgpath) as tfo:
#                 metapath = os.path.join(tfo.getnames()[0], metafile)
#                 with tfo.extractfile(metapath) as mfo:
#                     metalines = mfo.read().decode().splitlines()

#             for line in metalines:
#                 if line.startswith('Version: '):
#                     return V(line.split()[-1])

#         except:
#             pass

#     return V(os.path.basename(pkgpath.rstrip(extension)).split('-')[-1])


def main():
    """Start application."""
    installer = Installer()
    installer.main()


LOGGER = logging.getLogger(__program__)
STREAM = logging.StreamHandler()
FORMAT = logging.Formatter('%(name)s:%(levelname)s: %(message)s')
STREAM.setFormatter(FORMAT)
LOGGER.addHandler(STREAM)

if __name__ == '__main__':
    main()
