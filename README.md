# Glest

**Official Website: https://glest.github.io**

Data repository contains data such as:
- maps, scenarios, tutorials
- techs, tilesets
- themes for menu/gui
- translations

Glest is a network multi-player real-time strategy game engine.
It includes several factions,
each one consisting of many 3d characters. The factions are loosely
based on historical empires with added elements of fantasy, such as
mummies produced by Egyptian priests, Indian shamans who summon
thunderbirds for air assaults, and Norsemen who can build flying
valkries and "Thors". Start the game by harvesting natural resources,
then use the cash to produce an army. Single-player mode against the
CPU is also available.

go to the [Main Repository](https://github.com/Glest/glest-source)

## Submitting mods, tech trees, tilesets, maps, scenarios

Our goal is to help promote content that is submitted, and encourage
testing by users.

If you have created content and would like to add a link to it, please
[open an issue](https://github.com/Glest/glest-data/issues).

Include the following information:

* Subject:
  * [submission]`name of the mod`
* Body:
  * mod title, link, description.
  * Paste the output of `glest --validate...` into a gist at
          https://gist.github.com.


### Using Validate

```
--validate-techtrees=x=purgeunused=purgeduplicates=gitdelete=hideduplicates
                     	Where x is a comma-delimited list of techtrees to validate.
                     	glest --validate-techtrees=factionpack,vbros_pack_5
--validate-factions=x=purgeunused=purgeduplicates=hideduplicates
                     	Where x is a comma-delimited list of factions to validate.
                     	    --validate-techtrees
                     	example: glest --validate-factions=tech,egypt
--validate-scenario=x=purgeunused=gitdelete
                     	Where x is a single scenario to validate.
                     	example: glest --validate-scenario=stranded
--validate-tileset=x=purgeunused=gitdelete
                     	Where x is a single tileset to validate.
                     	example: glest --validate-tileset=desert2
```

### Maps

To suggest a map, please [open a ticket](https://github.com/Glest/glest-data/issues) and attach your map file.

## Contributed Content (not yet available on the Glest server)

* [MODS.md](https://github.com/Glest/glest-data/blob/develop/MODS.md)
* [TILESETS.md](https://github.com/Glest/glest-data/blob/develop/TILESETS.md)
* [SCENARIOS.md](https://github.com/Glest/glest-data/blob/develop/SCENARIOS.md)

### Blender models

[Modelling Information](https://glest.github.io/docs/modelling/)

We are working on creating and completing documentation. In the
meantime, please contact us with any questions or ideas. Thank you for
your interest in this project.

* [Contact / Community](https://github.com/Glest/glest-source#contact)
* [Contributing](https://github.com/Glest/glest-source/blob/develop/CONTRIBUTING.md)
