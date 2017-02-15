"""
Runs the testbed
"""
# TODO
# - version import on schemas failing
# - solution: rewrite with expect: http://stackoverflow.com/questions/28614911/opening-persistent-shell-in-python
    # - make docs commands in .travis.ymls seem to not work
    # - nose seems not to work sometimes
        # - problem: is using tbenv python, not correct ve python
# - add server, compliance repos
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import os
import shutil

import ga4gh.common.utils as utils


class CommandRunner(object):

    def runCommand(self, cmd):
        utils.log("CMD: '{}'".format(cmd))
        silent = True
        if VERBOSITY > 1:
            silent = False
        utils.runCommand(cmd, silent=silent)


class Repository(CommandRunner):
    """
    A repository
    """
    def __init__(self, repoDict):
        self.name = repoDict['name']
        self.branch = repoDict['branch']
        self.org = repoDict['org']
        self.egg = repoDict['egg']
        self.dependencies = repoDict['dependencies']
        self.runRepoTests = repoDict['runRepoTests']

    def git_url(self):
        url = "https://github.com/{}/{}.git --branch {}".format(
            self.org, self.name, self.branch)
        return url

    def clone(self):
        shutil.rmtree(self.name, True)
        self.runCommand("git clone {}".format(self.git_url()))

    def install_dependencies(self, virtualenv):
        with utils.performInDirectory(self.name):
            virtualenv.install_dependencies()

    def run_tests(self, virtualenv):
        with utils.performInDirectory(self.name):
            virtualenv.run_tests()


class CommonRepository(Repository):

    def run_tests(self, virtualenv):
        with utils.performInDirectory(self.name):
            virtualenv.run_with_python("run_tests_dev.py -p {}".format(
                virtualenv.get_python_path()))


class SchemaRepository(Repository):

    def install_dependencies(self, virtualenv):
        path = os.path.join(self.name, 'python')
        with utils.performInDirectory(path):
            virtualenv.install_dependencies()


class VirtualEnvironment(CommandRunner):
    """
    Provides methods to create and access a python virtual environment
    """
    def __init__(self, name, repo):
        self.name = name
        self.repo = repo

    def _dirs_above_prefix(self, num_dirs):
        return ''.join(['../' for _ in range(num_dirs)])

    def create(self):
        shutil.rmtree(self.name, True)
        virtualenv_cmd = "virtualenv {}".format(self.name)
        self.runCommand(virtualenv_cmd)
        self.abspath = os.path.abspath(self.name)

    def get_python_path(self):
        return "{}/bin/python".format(self.abspath)

    def get_pip_path(self):
        return "{}/bin/pip".format(self.abspath)

    def run_with_pip(self, cmd, dirs_above=1):
        pip_cmd = "{} {}".format(self.get_pip_path(), cmd)
        self.runCommand(pip_cmd)

    def run_with_python(self, cmd, dirs_above=1):
        python_cmd = "{} {}".format(self.get_python_path(), cmd)
        self.runCommand(python_cmd)

    def run_tests(self):
        test_cmd = "{}/bin/ga4gh_run_tests -p {}".format(
            self.abspath, self.get_python_path())
        self.run_with_python(test_cmd)

    def install_dependencies(self):
        install_cmd = "install -r dev-requirements.txt"
        if os.path.exists("constraints.txt"):
            self.create_constraints_file()
            install_cmd = \
                "install -r dev-requirements.txt -c constraints.txt"
        self.run_with_pip(install_cmd)

    def create_constraints_file(self):
        dependencies = self.repo.dependencies
        if not dependencies:
            return
        with open('constraints.txt', 'w') as constraintsFile,\
                open('constraints.txt.default', 'w') as defaultFile:
            for dependency in dependencies:
                repoDict = CONFIG[dependency]
                line = 'git+git://github.com/{}/{}.git@{}#egg={}\n'.format(
                    repoDict['org'], repoDict['name'],
                    repoDict['branch'], repoDict['egg'])
                constraintsFile.write(line)
                defaultFile.write(line)


def do_repo_tests():
    for repo in REPOSITORIES:
        if repo.runRepoTests:
            virtualenv_name = "ve-{}".format(repo.name)
            virtualenv = VirtualEnvironment(
                virtualenv_name, repo)
            virtualenv.create()
            repo.clone()
            repo.install_dependencies(virtualenv)
            repo.run_tests(virtualenv)


defaultVerbosity = 2


VERBOSITY = defaultVerbosity


REPO_ORDER = ['ga4gh-common', 'schemas', 'ga4gh-client']


CONFIG = {
    'ga4gh-common': {
        'name': 'ga4gh-common',
        'branch': 'testbed', 
        'org': 'dcolligan', 
        'egg': 'ga4gh_common', 
        'repoClass': CommonRepository,
        'dependencies': [],
        'runRepoTests': False,
    },
    'schemas': {
        'name': 'schemas',
        'branch': 'master',
        'org': 'dcolligan',
        'egg': 'ga4gh_schemas',
        'repoClass': SchemaRepository,
        'dependencies': ['ga4gh-common'],
        'runRepoTests': True,
    },
    'ga4gh-client': {
        'name': 'ga4gh-client',
        'branch': 'master',
        'org': 'ga4gh',
        'egg': 'ga4gh_client',
        'repoClass': Repository,
        'dependencies': ['ga4gh-common', 'schemas'],
        'runRepoTests': True,
    },
}


REPOSITORIES = []
for repoName in REPO_ORDER:
    repoDict = CONFIG[repoName]
    repo = repoDict['repoClass'](repoDict)
    REPOSITORIES.append(repo)



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbosity", type=int,
            default=defaultVerbosity,
            help="verbosity level, defaults to {}".format(defaultVerbosity))
    args = parser.parse_args()
    VERBOSITY = args.verbosity
    do_repo_tests()


if __name__ == '__main__':
    main()
