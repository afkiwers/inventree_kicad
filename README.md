# InvenTree KiCad - HTTP Library Plugin

> ⚠️ This plugin is currently in an early alpha state and has a fair few hard-coded bits for proof-of-concept purposes.

KiCad conform API endpoint plugin for [InvenTree](https://inventree.org)  to display and use InvenTree parts in KiCad's parts library tool. This plugin provides metadata only and requires matching symbol and footprint libraries within the KiCad EDA.

## Usage

### Select Categories which show up in KiCad

Opening the admin backend, one can add [categories](#select-categories-which-show-up-in-kicad) by simply selecting from available ones. The API will only provide parts from those categories.

> ℹ️ If no categories are chosen, the plugin will display all available.

## FAQ

### Why does this plugin need the App Mixin?

This plugin uses the App Mixin to add a custom model to the database to manage the selected categories. Otherwise, Kicad symbol chooser would be cluttered with every single category (See [Categories](#select-categories-which-show-up-in-kicad))

### Why does this plugin need the Url Mixin?

This plugin uses the Url Mixin to expose custom API endpoints which are conform with KiCads REST API requirements.

