# ZetaGlest

**Official Website: https://zetaglest.github.io**

Data repository contains data such as:
- maps, scenarios, tutorials
- techs, tilesets
- themes for menu/gui
- translations

ZetaGlest is a network multi-player real-time strategy game engine.
It's shipped with the ZetaPack mod, which includes several factions,
each one consisting of many 3d characters. The factions are loosely
based on historical empires with added elements of fantasy, such as
mummies produced by Egyptian priests, Indian shamans who summon
thunderbirds for air assaults, and Norsemen who can build flying
valkries and "Thors". Start the game by harvesting natural resources,
then use the cash to produce an army. Single-player mode against the
CPU is also available.

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

[Modelling Information](https://zetaglest.github.io/docs/modelling/)

We are working on creating and completing documentation. In the
meantime, please contact us with any questions or ideas. Thank you for
your interest in this project.

* [Contact / Community](https://github.com/ZetaGlest/zetaglest-source#contact)
* [Contributing](https://github.com/ZetaGlest/zetaglest-source/blob/develop/CONTRIBUTING.md)
