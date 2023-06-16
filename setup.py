# -*- coding: utf-8 -*-

import setuptools

from inventree_kicad.version import PLUGIN_VERSION

with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

setuptools.setup(
    name="inventree-kicad-plugin",

    version=PLUGIN_VERSION,

    author="Andre Iwers",

    author_email="iwers11@gmail.com",

    description="KiCad EDA conform API endpoint for KiCad's parts library tool",

    long_description=long_description,

    long_description_content_type='text/markdown',

    keywords="inventree kicad",

    url="https://github.com/afkiwers/inventree-kicad-plugin",

    license="MIT",

    packages=setuptools.find_packages(),

    install_requires=[
        "django==3.2.19"
    ],

    setup_requires=[
        "wheel",
        "twine",
    ],

    python_requires=">=3.6",

    entry_points={
        "inventree_plugins": [
            "KiCadAPIPlugin = inventree_kicad.KiCadLibraryPlugin:KiCadLibraryPlugin"
        ]
    },
    
    include_package_data=True,
)
