import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

README = read('README.rst')

setup(
    name = "django_compressor",
    version = "0.1",
    url = 'http://github.com/spurfly/django-autodot',
    license = 'BSD',
    description = "Automatically generates doT.js templates from parts of django ones.",
    long_description = README,

    author = 'Jameson Quinn',
    author_email = 'jameson.quinn@gmail.com',
    packages = [
        'autodot',
        'autodot.templatetags',
    ],
    package_data = {
        'autodot': [
                'templates/autodot/*.html',
            ],
    },
    install_requires = [
        'BeautifulSoup',
        'django_compressor',
    ],
    classifiers = [
        'Development Status :: 3 - Pre-Alpha',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: JavaScript',
        'Topic :: Internet :: WWW/HTTP',
    ],
    zip_safe = False,
)
