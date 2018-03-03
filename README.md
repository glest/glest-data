# ZetaGlest Data

> Repository contains data such as:
> * maps, scenarios, tutorials
> * techs, tilesets
> * themes for menu/gui
> * translations

ZetaGlest is a fork of [MegaGlest](http://megaglest.org/), a network
multi-player cross-platform 3D real-time strategy (RTS) game, where you
control the armies of one of eight different factions: Tech, Magic,
Egypt, Indians, Norsemen, Persian, Elves or Romans. The game is played
in one of 17 naturally looking settings, which, like the unit models,
are crafted with great attention to detail. A lot of additional game
data can be downloaded from within the game at no cost.

go to the [Main Repository](https://github.com/ZetaGlest/zetaglest-source)

## Submitting mods, tech trees, tilesets, maps, scenarios

Our goal is to help promote content that is submitted, and encourage
testing by users.

If you have created content and would like to add a link to it, please
[open an issue](https://github.com/ZetaGlest/zetaglest-data/issues).

Include the following information:

* Subject:
  * [submission]`name of the mod`
* Body:
  * mod title, link, description.
  * Paste the output of `zetaglest --validate...` into a gist at
          https://gist.github.com.


### Using Validate

```
--validate-techtrees=x=purgeunused=purgeduplicates=gitdelete=hideduplicates
                     	Where x is a comma-delimited list of techtrees to validate.
                     	zetaglest --validate-techtrees=megapack,vbros_pack_5
--validate-factions=x=purgeunused=purgeduplicates=hideduplicates
                     	Where x is a comma-delimited list of factions to validate.
                     	    --validate-techtrees
                     	example: zetaglest --validate-factions=tech,egypt
--validate-scenario=x=purgeunused=gitdelete
                     	Where x is a single scenario to validate.
                     	example: zetaglest --validate-scenario=stranded
--validate-tileset=x=purgeunused=gitdelete
                     	Where x is a single tileset to validate.
                     	example: zetaglest --validate-tileset=desert2
```

### Maps

To suggest a map, please [open a ticket](https://github.com/ZetaGlest/zetaglest-data/issues) and attach your map file.

## Contributed Content (not yet available on the ZetaGlest server)

* [MODS.md](https://github.com/ZetaGlest/zetaglest-data/blob/develop/MODS.md)
* [TILESETS.md](https://github.com/ZetaGlest/zetaglest-data/blob/develop/TILESETS.md)
* [SCENARIOS.md](https://github.com/ZetaGlest/zetaglest-data/blob/develop/SCENARIOS.md)

### Other artwork (sounds, graphics, 3d models, icons)

### Blender models

[Model Specifications](https://zetaglest.github.io/docs/model_specifications.html)

We are working on creating and completing documentation. In the
meantime, please contact us with any questions or ideas. Thank you for
your interest in this project.

* [Contact / Community](https://github.com/ZetaGlest/zetaglest-source#contact)
* [Contributing](https://github.com/ZetaGlest/zetaglest-source/blob/develop/CONTRIBUTING.md)
