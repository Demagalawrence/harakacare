from setuptools import setup, find_packages

setup(
    name="harakacare",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'Django>=5.0',
        'djangorestframework',
    ],
)
