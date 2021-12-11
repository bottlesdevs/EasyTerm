from setuptools import setup

setup(
    name='EasyTerm',
    description='An easy-to-bundle GTK terminal emulator',
    author='Mirko brombin',
    author_email='send@mirko.pm',
    version='0.1.5',
    packages=['easyterm'],
    scripts=['easyterm/easyterm.py'],
    url='https://github.com/bottlesdevs/EasyTerm',
    license='GPLv3',
    long_description=open('README.md').read()
)