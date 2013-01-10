from paver.easy import *
from paver.path import path
from paver.setuputils import setup


VERSION = (0, 1, 0, "")

setup(
    name="pathfinder",
    description="A straightforward HTTP request router",
    packages=["pathfinder"],
    version=".".join(filter(None, map(str, VERSION))),
    author="Travis J Parker",
    author_email="teepark@jawbone.com",
    #url="",
    #license="BSD",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python",
    ],
)

MANIFEST = (
    "setup.py",
    "paver-minilib.zip",
)

@task
def manifest():
    path('MANIFEST.in').write_lines('include %s' % x for x in MANIFEST)

@task
@needs('generate_setup', 'minilib', 'manifest', 'setuptools.command.sdist')
def sdist():
    pass

@task
def clean():
    for p in map(path, (
        'pathfinder.egg-info', 'dist', 'build', 'MANIFEST.in', 'docs/build')):
        if p.exists():
            if p.isdir():
                p.rmtree()
            else:
                p.remove()
    for p in path(__file__).abspath().parent.walkfiles():
        if p.endswith(".pyc") or p.endswith(".pyo"):
            p.remove()