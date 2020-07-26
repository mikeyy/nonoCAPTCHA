import codecs
import os
from importlib.machinery import SourceFileLoader

from setuptools import setup, find_packages

module_name = "goodbyecaptcha"

module = SourceFileLoader(
    module_name, os.path.join(module_name, "__init__.py")
).load_module()


def load_requirements(fname):
    """ load requirements from a pip requirements file """
    with open(fname) as f:
        line_iter = (line.strip() for line in f.readlines())
        return [line for line in line_iter if line and line[0] != "#"]


setup(
    name=module_name.replace("_", "-"),
    version=module.__version__,
    author=module.__author__,
    author_email=module.authors_email,
    license=module.__license__,
    description=module.package_info,
    url="https://github.com/MacKey-255/GoodByeCatpcha",
    long_description=codecs.open("README.rst", encoding="utf-8").read(),
    platforms="all",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        'Environment :: Console',
        'Environment :: Web Environment',
        'Environment :: Plugins',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Operating System :: Unix",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: JavaScript",
        "Topic :: Scientific/Engineering",
        'Topic :: Scientific/Engineering :: Image Recognition',
        'Topic :: Scientific/Engineering :: Information Analysis',
        "Topic :: Software Development :: Libraries",
        'Topic :: Software Development :: Libraries :: Python Modules',
        "Topic :: Utilities"
    ],
    keywords=(
        'captcha, recaptcha, Python3, google, cloudflare, mitm,'
        'solver captcha, automate solver, web scraping, botting'
        'goodbyecaptcha, solver recaptcha, image recognition'
    ),
    package_data={'data': ['*.*'], 'models': ['*.*']},
    include_package_data=True,
    packages=find_packages(),
    install_requires=load_requirements("requirements.txt"),
)
