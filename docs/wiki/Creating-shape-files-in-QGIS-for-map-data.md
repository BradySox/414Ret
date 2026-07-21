# Creating shape files in QGIS for map data

> **Adopted standard (2026-07-20).** This page mirrors the upstream
> [Creating shape files in QGIS for map data](https://github.com/dcs-retribution/dcs-retribution/wiki/Creating-shape-files-in-QGIS-for-map-data)
> guide, adopted as the 414th's own standard for landmap data. The workflow and tool
> paths are identical in this fork (`unshipped_data/arcgis_maps/` and
> `resources/tools/arcgis_landmap_import.py` both exist here). When upstream revises
> their page, refresh this one.

> ⚠️ **Work in progress.** This guide is not finished — the DEM slope-analysis section
> (4.2.1) ends before the final steps, but the land/sea workflow and the integration
> steps at the bottom are complete enough to be usable.

This guide will enable you to create data that the developers can use to enable support
for a new map. We will use QGIS, an open-source GIS program, to generate this data from
various open sources. You need to have QGIS installed, preferably a 3.x+ version with the
GRASS processing toolbox.
https://www.qgis.org/en/site/forusers/download.html

Here is some basic information about what a .SHP shapefile is:
https://en.wikipedia.org/wiki/Shapefile

**Shapefile support was introduced in DCS Liberation 6.0 (pre-Retribution numbering) and
enables you to use a dedicated GIS program to create data where the game should and
should not allow frontline units and ships to be. QGIS is a very powerful program and you
can arrive at the end product in a near infinite number of ways. In this guide one
possible workflow is outlined that tries to take as many factors into account for
problem-free spawning. It will still be up to the campaign designer to use judgement
where to place the frontlines to avoid troublesome behaviour.**

Here are the basic steps you need to take:

## 1) Map projection

Some basic concepts about map projections can be learned here:
https://en.wikipedia.org/wiki/Map_projection

For DCS you need to know that the DCS maps use a UTM projection (meaning coordinates are
measured in meters as opposed to degrees, basically), and we need to find out the UTM
tile for the map we are working on.
https://en.wikipedia.org/wiki/Universal_Transverse_Mercator_coordinate_system

### 1.1 Find the correct projection for the map

Through pydcs we already have the center meridian of the map, meaning we can figure out
the proper UTM projection
(https://github.com/pydcs/dcs/blob/master/tools/export_map_projection.py).

The snapshot below is a **partial** copy and only covers a handful of theaters. Newer
maps (e.g. Sinai, Kola, Germany Cold War, Iraq, Afghanistan) are not listed here — always
check the live
[`export_map_projection.py`](https://github.com/pydcs/dcs/blob/master/tools/export_map_projection.py)
in pydcs for the current, authoritative list of central meridians.

```
CENTRAL_MERIDIANS = {
    "caucasus": 33,
    "falklands": -57,
    "nevada": -117,
    "normandy": -3,
    "persiangulf": 57,
    "thechannel": 3,
    "syria": 39,
    "marianaislands": 147,
    # ... see pydcs for the full, current list (Sinai, Kola, GermanyCW, Iraq, Afghanistan, ...)
}
```

We can use this
[map](https://www.arcgis.com/apps/View/index.html?appid=7fa64a25efd0420896c3336dc2238475)
to check out different UTM zones. By clicking on the UTM tile you see the central
projection. The map central projection is not necessarily in the center of the map. In
the case of South Atlantic it begun as only the Falklands islands so the projection for
the whole map is UTM 21S (S for South hemisphere).
![FindProjection](https://user-images.githubusercontent.com/20801481/202789407-6471dbd5-7b59-4cc6-8ab6-08d004b6ddad.jpg)

### 1.2 Set up your QGIS project

Then it is a matter of making a new project in QGIS and setting the project CRS to be
this.
![Projection](https://user-images.githubusercontent.com/20801481/189474094-89e78347-23b5-440a-b4b5-44862b472276.JPG)

### 1.3 Visualizing your map by using tiles for satmaps or OpenStreetMaps live view

You can add XYZ tiles from this python script to add in a bunch of online satmap tile
layers you can use:
https://raw.githubusercontent.com/klakar/QGIS_resources/master/collections/Geosupportsystem/python/qgis_basemaps.py

## 2) Outlining the game area

In the correct projection you can now create a new vector polygon layer and add the game
area as an overlay. Preferably by getting actual coordinates from the ME as opposed to
freehand editing. Layer -> Create Layer -> New Shapefile Layer
![ShapefileGameArea](https://user-images.githubusercontent.com/20801481/189474224-4870e056-9054-4f6a-96c7-936bb1ce48a8.JPG)

Make sure you use the project CRS (projection) and that it is a polygon. Also make sure
you save it to a location so you can retrieve it the next time you open the project. You
can save the temporary layer by right clicking the feature in the layer view and select
Save Feature As. This is also handy to check during the save that the projection is what
you expect it to be.

![GameArea_makepoly](https://user-images.githubusercontent.com/20801481/189474417-cd685745-bce4-4626-b2ac-e0ba62176c4f.JPG)

## 3) Oceans

### 3.1 Getting the source data and processing it

For the ocean, download the OSM Ocean Polygon files (source
https://osmdata.openstreetmap.de/data/water-polygons.html). These are WGS84-projected
chunks of ocean. Select all the vector objects that are relevant to the map, and use the
Vector -> Geoprocessing -> Dissolve command to merge the cells into one object. This will
output a new temporary layer (can be slow to do). This layer we can now save and
reproject to the relevant UTM projection, like UTM 21S for the Falklands map. Right click
on the temporary output layer and select Export -> Save Feature As... Be sure to
reproject only after dissolve or you will potentially get gaps in the ocean file.
![image](https://user-images.githubusercontent.com/20801481/202793894-95c1c32e-fc72-4edf-ac21-1f0be10f1016.png)

Once you have the ocean file dissolved and projected to the correct UTM projection you
can clip it to the game area overlay (Vector -> Geoprocessing -> Clip).

![ClipSea](https://user-images.githubusercontent.com/20801481/191521040-e7a0787a-5c82-48d9-9e6d-8f9ab9a493e2.JPG)

Once again this is saved as a temporary file which you now can save to disk.

### 3.2 Generating Retribution-usable land and sea data

The final step is now to generate the land mass for Retribution as well as the actual
ocean. Remember, we want to keep this data as lightweight as possible so we will first
simplify the data. Use Vector -> Geometry tools -> Simplify and try different values.

![Simplify](https://user-images.githubusercontent.com/20801481/191523064-c2a99d11-6e8e-4006-9e90-d4fd17fbce98.JPG)

A tolerance value of 250 is probably fine at this stage but you can go more aggressive if
you want to.

After we simplified the data, now is the time to generate land data and ocean data. We
will use the basic, simplified ocean to generate both the land and sea area. To make sure
we get some margins so you can't accidentally move the carrier right to the beach or
spawn units in the sea, use a buffer zone from the shore inland for the land map and a
buffer zone from the shore out towards the sea. In the South Atlantic map the author
elected for a 750m buffer inland and a 1500m buffer out to sea. The 1500m buffer out to
sea means a lot of the smaller sounds and bays will be eliminated, further simplifying
our data.

![Buffer](https://user-images.githubusercontent.com/20801481/191524446-24c970f2-21da-4127-90eb-320d7e5b47f8.JPG)

![image](https://user-images.githubusercontent.com/20801481/202790839-50c00420-ba95-484c-b680-f7dfa6308dee.png)

Here we can see our ocean that is buffered outwards from the shore 1500m.

To actually get land area as opposed to a sea that reaches inland 750m we need to use the
difference command (Vector -> Geoprocessing -> Difference).
![image](https://user-images.githubusercontent.com/20801481/202793193-1f9c069a-6f59-43b3-8d1c-eb1ebb2d5be0.png)

Make sure you have the Game area as input layer and the buffered sea as overlay.

You should now have something like this:

![image](https://user-images.githubusercontent.com/20801481/202793331-76950224-4a3e-4326-9de6-cc371a3e72ed.png)

**Congratulations, you now have the land and sea data!**

## 4) Exclusion data

Naturally, not all of the landmass is suitable to have warring armies on it. We should at
least make lakes and rivers off-limits, and big cities too. We need to get source data to
work with, and process this data to make it as lightweight as possible.

### 4.1 Downloading OSM vector source data

From the link below you can find collections of OSM source data that you can download and
add to your QGIS project:
https://download.geofabrik.de/index.html

The easiest way is to download the SHP files for individual countries — e.g. for the
South Atlantic map, Argentina and Chile — and add the layers thought necessary to the
map: water, waterways and landuse.

### 4.1.1 Processing the data

Once we have all the files, we need to do the following:

* Resave the files in the proper projection
* Clip the files to only encompass the game area
* Simplify the data
* Buffer lakes and rivers slightly

This can be done using the same techniques we learned in section 3.

### 4.2 Downloading DEM data for slope analysis

This step is potentially optional, but if the map contains many mountains and steep
terrain like the South Atlantic map does, it can be worthwhile to do.

Use NASA's EarthData Search portal and search for **NASADEM**:
https://search.earthdata.nasa.gov/search?q=nasadem

We will use NASA's EarthData Search portal to find DEM data. The NASADEM Merged DEM
Global 1 arc second V001 dataset is reasonably high-resolution and free to use. You will
need to register for the service, log in, search the site for the correct dataset, and
then draw an outline of the area you want to create a download link.

![image](https://user-images.githubusercontent.com/20801481/202798042-3b9a1d61-1b6a-47ea-9539-411ccb41c9e6.png)

### 4.2.1 Processing the DEM files

To make editing easier, you will want to merge all your cells into one file using
Raster -> Miscellaneous -> Merge. It can still be useful to retain one or two cells for
testing commands on a smaller dataset so you are sure you get what you want.

Now that we have the DEM file, we need to visualize the data. At this point, you should
probably have an instance of DCS open so you can cross-reference the in-game view to
better judge what slopes are fine and what are excessive.

We will use the Raster -> Analysis -> Slope tool to make a slope map.

![image](https://user-images.githubusercontent.com/20801481/202802845-300c2cac-2009-4e01-a3c4-0fccbe6f474e.png)

The slope map can be visualized by right clicking on the layer and selecting properties,
and selecting the Symbology tab. Here we will select "Singleband Pseudocolor" and play
around with the values to find what slope value should be the cutoff, values above which
are considered impassable.

![image](https://user-images.githubusercontent.com/20801481/202803476-32ca60dc-2d30-40e1-a88d-078f89e67b0c.png)

![image](https://user-images.githubusercontent.com/20801481/202803996-38d2dd8b-4daf-4d3d-82fb-0e04defe0151.png)

By zooming out and changing color palettes and values of various colors you can probably
find a value that seems reasonable. In the image above the red-value areas are probably
bad for ground units while the other colors are passable.

Once you have settled on a cutoff slope value, the remaining workflow (outline — exact
tools may vary by QGIS version) is to turn the impassable slope areas into an exclusion
polygon and merge them with the rest of your exclusion data:

1. Threshold the slope raster to the impassable areas — e.g. use
   **Raster -> Raster Calculator** to produce a binary raster (`1` where slope exceeds
   your cutoff, `0` otherwise).
2. Convert that raster to vector polygons with
   **Raster -> Conversion -> Polygonize**, then filter to keep only the impassable (`1`)
   polygons.
3. Clean the result: **Simplify** and, if needed, a small **Buffer**, then **Dissolve**
   to merge adjacent polygons.
4. Merge these slope-derived polygons with your other exclusion layers (lakes, rivers,
   cities from section 4.1) into a single exclusion layer, and save it as your
   `exclusion` shapefile.

## 5) Integrating your data into Retribution

Once you have your three shapefiles (land, sea, and exclusion), integrate them:

1. Place the shapefiles under `unshipped_data/arcgis_maps/<theater>/`, in the `land/`,
   `sea/`, and `exclusion/` subfolders respectively (use the theater's Retribution name,
   e.g. `falklands`).
2. Run the importer to produce the pickled landmap used at runtime:
   `resources/tools/arcgis_landmap_import.py <theater>`. This writes the landmap to the
   correct location via `TheaterLoader.landmap_path` (loaded at runtime by
   `game/theater/landmap.py`).
3. Test in-game, then submit your shapefiles (and any changes) as a Pull Request so the
   map can be supported in a release.
