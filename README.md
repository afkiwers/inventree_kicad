# inventree-kicad-plugin

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> :warning: This plugin is currently in alpha. Also, KiCad does not support REST APIs just yet but hopefully will soon.

KiCad EDA conform API endpoint [InvenTree](https://inventree.org) plugin for KiCad's parts library tool. This plugin provides metadata only and requires matching symbol and footprint libraries within the KiCad EDA.

## Installation

Install this plugin as follows:

1. Make sure you allow the use of the url integration and app integration (see [Why does this plugin need the app mixin?](#why-does-this-plugin-need-the-app-mixin))

2. Goto Settings > Plugins > Install Plugin, set `inventree-kicad-plugin` as package name and `git+https://github.com/afkiwers/inventree-kicad-plugin` as source URL, confirm and click submit.

3. Restart your server and activate the plugin.

4. Stop your server and run `invoke update` (for docker installs it is `docker-compose inventree-server invoke update`). This ensures that all migrations run and the static files get collected. You can now start your server again and start using the plugin.

## Usage

### Select Categories which show up in KiCad

Opening the admin backend, one can add [categories](#select-categories-which-show-up-in-kicad) by simply selecting from available ones. The API will only provide parts from those categories.
> :information_source: If no categories are chosen, the plugin will display all available.

## FAQ

### Why does this plugin need the App Mixin?

This plugin uses the App Mixin to add a custom model to the database to manage the selected categories. Otherwise, Kicad symbol chooser would be cluttered with every single category (See [Categories](#select-categories-which-show-up-in-kicad))

### Why does this plugin need the Url Mixin?

This plugin uses the Url Mixin to expose custom API endpoints which are conform with KiCads REST API requirements.
