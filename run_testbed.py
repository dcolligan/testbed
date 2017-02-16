"""
Runs the testbed

By default, this means:
- Create a bash script file for each repository that downloads the
    repository and runs its tests; execute that file

(We can't script this purely from python because we need a persistent
shell running an appropriate virtual environment for when deeper commands
call 'python', etc.)
"""
# TODO
# - version import on schemas failing
# - 'no module named protocol' on client, server
# - add compliance repo
# - move config to different module
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import os

import ga4gh.common.utils as utils


class ShellEnvironment(object):

    def __init__(self, fileName):
        self.fileName = fileName
        self.fileHandle = open(self.fileName, 'w')
        utils.log("=== Writing '{}' ===".format(self.fileName))

    def writeCommand(self, cmd):
        utils.log("CMD: '{}'".format(cmd))
        self.fileHandle.write(cmd + '\n')

    def writeCommands(self, cmds):
        for cmd in cmds:
            self.writeCommand(cmd)

    def execute(self):
        self.fileHandle.close()
        cmd = 'bash {}'.format(self.fileName)
        utils.runCommand(cmd)


class Repository(object):

    def __init__(self, repoDict):
        self.name = repoDict['name']
        self.branch = repoDict['branch']
        self.org = repoDict['org']
        self.egg = repoDict['egg']
        self.dependencies = repoDict['dependencies']
        self.runRepoTests = repoDict['runRepoTests']
        self.constraintsDir = repoDict['constraintsDir']
        self.vename = None
        self.veabspath = None

    def _perform_in_dir_cmds(self, path, cmds):
        first = ['pushd {}'.format(path)]
        last = ['popd']
        if isinstance(cmds, list):
            toReturn = first + cmds + last
        else:
            toReturn = first + [cmds] + last
        return toReturn

    def get_git_url(self):
        url = "https://github.com/{}/{}.git --branch {}".format(
            self.org, self.name, self.branch)
        return url

    def clone_cmds(self):
        cmds = [
            "rm -rf {}".format(self.name),
            "git clone {}".format(self.get_git_url()),
        ]
        return cmds

    def install_dependencies_cmds(self):
        constraintsDir = self.name
        if self.constraintsDir is not None:
            constraintsDir = os.path.join(
                self.name, self.constraintsDir)
        cmds = self._perform_in_dir_cmds(
            constraintsDir,
            self._install_dependencies_cmds())
        return cmds

    def _install_dependencies_cmds(self):
        install_cmd = "install -r dev-requirements.txt"
        if os.path.exists("constraints.txt"):
            install_cmd = \
                "install -r dev-requirements.txt -c constraints.txt"
        return self.run_with_ve_pip_cmd(install_cmd)

    def run_with_ve_pip_cmd(self, cmd):
        pip_cmd = "{} {}".format(self.get_ve_pip_path(), cmd)
        return pip_cmd

    def get_ve_pip_path(self):
        return "{}/bin/pip".format(self.veabspath)

    def run_tests_cmds(self):
        cmds = self._perform_in_dir_cmds(
            self.name,
            self._run_tests_cmds())
        return cmds

    def _run_tests_cmds(self):
        test_cmd = "{}/bin/ga4gh_run_tests".format(
            self.veabspath)
        return self.run_with_ve_python_cmd(test_cmd)

    def run_with_ve_python_cmd(self, cmd):
        python_cmd = "{} {}".format(self.get_ve_python_path(), cmd)
        return python_cmd

    def create_ve_cmds(self, vename):
        cmds = [
            'rm -rf {}'.format(vename),
            'virtualenv {}'.format(vename)
        ]
        self.vename = vename
        self.veabspath = os.path.join(
            os.path.abspath(os.getcwd()), vename)
        return cmds

    def enter_ve_cmd(self):
        return 'source {}'.format(self.get_ve_activate_path())

    def leave_ve_cmd(self):
        return 'deactivate'

    def get_ve_activate_path(self):
        return "{}/bin/activate".format(self.veabspath)

    def get_ve_python_path(self):
        return "{}/bin/python".format(self.veabspath)

    def create_constraints_file_cmds(self):
        if not self.dependencies:
            return []
        constraintsFileName = 'constraints.txt'
        defaultFileName = 'constraints.txt.default'
        constraintsPath = os.path.join(self.name, constraintsFileName)
        defaultPath = os.path.join(self.name, defaultFileName)
        if self.constraintsDir is not None:
            constraintsPath = os.path.join(
                self.name, self.constraintsDir, constraintsFileName)
            defaultPath = os.path.join(
                self.name, self.constraintsDir, defaultFileName)
        cmds = []
        clearConstraintsCmd = 'echo -n > {}'.format(constraintsPath)
        clearDefaultCmd = 'echo -n > {}'.format(defaultPath)
        cmds.append(clearConstraintsCmd)
        cmds.append(clearDefaultCmd)
        for dependency in self.dependencies:
            repoDict = CONFIG[dependency]
            line = 'git+git://github.com/{}/{}.git@{}#egg={}'.format(
                repoDict['org'], repoDict['name'],
                repoDict['branch'], repoDict['egg'])
            constraintsCmd = "echo '{}' >> {}".format(line, constraintsPath)
            defaultCmd = "echo '{}' >> {}".format(line, defaultPath)
            cmds.append(constraintsCmd)
            cmds.append(defaultCmd)
        return cmds


class CommonRepository(Repository):

    def run_tests_cmds(self):
        cmds = self._perform_in_dir_cmds(
            self.name,
            self.run_with_ve_python_cmd(
                "run_tests_dev.py".format()))
        return cmds


def do_repo_tests():
    for repo in REPOSITORIES:
        if repo.runRepoTests:
            shell = ShellEnvironment('{}-tests.sh'.format(repo.name))
            virtualenv_name = "ve-{}".format(repo.name)
            shell.writeCommands(repo.create_ve_cmds(virtualenv_name))
            shell.writeCommand(repo.enter_ve_cmd())
            shell.writeCommands(repo.clone_cmds())
            shell.writeCommands(repo.create_constraints_file_cmds())
            shell.writeCommands(repo.install_dependencies_cmds())
            shell.writeCommands(repo.run_tests_cmds())
            shell.writeCommand(repo.leave_ve_cmd())
            shell.execute()


defaultVerbosity = 2


VERBOSITY = defaultVerbosity


REPO_ORDER = ['ga4gh-common', 'schemas', 'ga4gh-client', 'server']


CONFIG = {
    'ga4gh-common': {
        'name': 'ga4gh-common',
        'branch': 'master',
        'org': 'dcolligan',
        'egg': 'ga4gh_common',
        'repoClass': CommonRepository,
        'dependencies': [],
        'runRepoTests': True,
        'constraintsDir': None,
    },
    'schemas': {
        'name': 'schemas',
        'branch': 'master',
        'org': 'dcolligan',
        'egg': 'ga4gh_schemas',
        'repoClass': Repository,
        'dependencies': ['ga4gh-common'],
        'runRepoTests': False,
        'constraintsDir': 'python',
    },
    'ga4gh-client': {
        'name': 'ga4gh-client',
        'branch': 'master',
        'org': 'ga4gh',
        'egg': 'ga4gh_client',
        'repoClass': Repository,
        'dependencies': ['ga4gh-common', 'schemas'],
        'runRepoTests': False,
        'constraintsDir': None,
    },
    'server': {
        'name': 'server',
        'branch': 'master',
        'org': 'ga4gh',
        'egg': 'server',
        'repoClass': Repository,
        'dependencies': ['ga4gh-common', 'schemas', 'ga4gh-client'],
        'runRepoTests': False,
        'constraintsDir': None,
    },
}


REPOSITORIES = []
for repoName in REPO_ORDER:
    repoDict = CONFIG[repoName]
    repo = repoDict['repoClass'](repoDict)
    REPOSITORIES.append(repo)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbosity", type=int,
        default=defaultVerbosity,
        help="verbosity level, defaults to {}".format(defaultVerbosity))
    args = parser.parse_args()
    VERBOSITY = args.verbosity
    do_repo_tests()


if __name__ == '__main__':
    main()
