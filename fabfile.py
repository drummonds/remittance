from fabric.api import task, local


@task
def clean():
    """remove all build, test, coverage and Python artifacts"""
    pass


@task
def install():
    """Install the package to the active Python's site-packages"""
    clean()
    local('python setup.py install')


@task
def dist():
    """builds source and wheel package"""
    clean()
    local('python setup.py sdist')
    local('python setup.py bdist_wheel')


@task(alias="r")
def release():
    """package and upload a release"""
    clean()
    local('python setup.py sdist upload')
    local('python setup.py bdist_wheel upload')
