# -*- coding: utf-8 -*-

import setuptools

from inventree_kicad.version import KICAD_PLUGIN_VERSION

with open('README.md', encoding='utf-8') as f:
    long_description = f.read()


setuptools.setup(
    name="inventree-kicad-plugin",

    version=KICAD_PLUGIN_VERSION,

    author="Andre Iwers",

    author_email="iwers11@gmail.com",

    description="KiCad HTTP library plugin for InvenTree",

    long_description=long_description,

    long_description_content_type='text/markdown',

    keywords="inventree kicad pcb schematic inventory",

    url="https://github.com/afkiwers/inventree_kicad",

    license="MIT",

    packages=setuptools.find_packages(),

    install_requires=[],

    include_package_data=True,

    setup_requires=[
        "wheel",
        "twine",
    ],

    python_requires=">=3.9",

    entry_points={
        "inventree_plugins": [
            "KiCadLibraryPlugin = inventree_kicad.KiCadLibraryPlugin:KiCadLibraryPlugin"
        ]
    },
)
