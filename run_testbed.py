"""
Runs the testbed
"""
# TODO
# - replace constraints files with appropriate branch names
# - make docs commands in .travis.ymls seem to not work
# - nose seems not to work sometimes
    # - make an alias to python that points to the python virtual env
    # - or install nose beforehand?
# - add server, compliance repos
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import shutil

import ga4gh.common.utils as utils


class Configuration(object):
    """
    The testbed configuration
    """
    def __init__(self, repositories):
        self.repositories = repositories
        self.run_repo_tests = True


class Repository(object):
    """
    A repository for the configuration
    """
    def __init__(self, name, branch, org):
        self.name = name
        self.branch = branch
        self.org = org

    def git_url(self):
        url = "https://github.com/{}/{}.git --branch {}".format(
            self.org, self.name, self.branch)
        return url

    def clone(self):
        shutil.rmtree(self.name, True)
        utils.runCommand("git clone {}".format(self.git_url()))

    def install_dependencies(self, virtualenv):
        with utils.performInDirectory(self.name):
            virtualenv.install_dependencies()

    def run_tests(self, virtualenv):
        with utils.performInDirectory(self.name):
            virtualenv.run_tests()


class CommonRepository(Repository):

    def run_tests(self, virtualenv):
        with utils.performInDirectory(self.name):
            virtualenv.run_with_python("run_tests_dev.py")


class SchemaRepository(Repository):

    def install_dependencies(self, virtualenv):
        path = os.path.join(self.name, 'python')
        with utils.performInDirectory(path):
            virtualenv.install_dependencies()


class VirtualEnvironment(object):
    """
    Provides methods to create and access a python virtual environment
    """
    def __init__(self, name):
        self.name = name

    def _dirs_above_prefix(self, num_dirs):
        return ''.join(['../' for _ in range(num_dirs)])

    def create(self):
        shutil.rmtree(self.name, True)
        virtualenv_cmd = "virtualenv {}".format(self.name)
        utils.runCommand(virtualenv_cmd)
        self.abspath = os.path.abspath(self.name)

    def run_with_pip(self, cmd, dirs_above=1):
        pip_cmd = "{}/bin/pip {}".format(self.abspath, cmd)
        utils.runCommand(pip_cmd)

    def run_with_python(self, cmd, dirs_above=1):
        python_cmd = "{}/bin/python {}".format(self.abspath, cmd)
        utils.runCommand(python_cmd)

    def run_tests(self):
        test_cmd = "{}/bin/ga4gh_run_tests".format(self.abspath)
        self.run_with_python(test_cmd)

    def install_dependencies(self):
        install_cmd = "install -r dev-requirements.txt"
        if os.path.exists("constraints.txt"):
            install_cmd = \
                "install -r dev-requirements.txt -c constraints.txt"
        self.run_with_pip(install_cmd)



def setup():
    CONFIG = [
        ['ga4gh-common', 'master', 'ga4gh', CommonRepository],
        ['schemas', 'testbed', 'dcolligan', SchemaRepository],
        ['ga4gh-client', 'master', 'ga4gh', Repository],
    ]
    repositories = []
    for repo, branch, org, repo_class in CONFIG:
        repository = repo_class(repo, branch, org)
        repositories.append(repository)
    config = Configuration(repositories)
    return config


def do_repo_tests(config):
    for repo in config.repositories:
        virtualenv_name = "ve-{}".format(repo.name)
        virtualenv = VirtualEnvironment(virtualenv_name)
        virtualenv.create()
        repo.clone()
        repo.install_dependencies(virtualenv)
        repo.run_tests(virtualenv)

def main():
    config = setup()
    if config.run_repo_tests:
        do_repo_tests(config)


if __name__ == '__main__':
    main()
