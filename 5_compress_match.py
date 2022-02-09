import grass.script as grass
import glob
import os
import sys
from datetime import datetime
import time

# folder containing the sentinel imagery preprocessed
foldin_global = 'path\to\input_folder\band_temp\'
# roi Shapefile
roi_in = 'path\to\roi'
res_in = 10  # GRASS Region target resolution L8

# CREATE OUTPUT FOLDER WITHIN THE INPUT FOLDER
folder_out = "path\to\output_folder\"


# SET REGION ACCORDING TO SHAPE AND RES
grass.run_command("v.in.ogr", input=roi_in, output="roi", overwrite=True)
grass.run_command("g.region", vect="roi", res=res_in, flags="a")

# get all files' and folders' names in the current directory
filenames = os.listdir(foldin_global)

for date in filenames:
    foldin = foldin_global+date+'\\'
    print(foldin)
    # GET DATES
    data = os.listdir(foldin)

    # # PROCESSING SCENES BY DATE
    name_list = []
    band_name_list = []
    # for d in ldates:
    for x in data:
        # if x.endswith('match.tiff') and x.find(d.strftime("%Y%m%d"))!=-1:
        if x.endswith('match.tiff') and x.find(date) != -1:
            imagery_name = (x.split(".")[0]).split("_")[0]
            bnd_int = int((x.split(".")[0]).split("_")[1])+1
            bnd = "B" + f"{bnd_int:02d}"
            name_list.append(str((x.split(".")[0]).split("_")[0]+'_'+bnd))
            # IMPORT BANDS
            grass.run_command("r.in.gdal", input="%s" % foldin+x, output="%s" % str((
                x.split(".")[0]).split("_")[0]+'_'+bnd), band=1, flags='ok', overwrite=True)

    # COMPRESS AND CREATE GROUP
    myInput = name_list
    grass.run_command("i.group", group='%s' % imagery_name,
                      subgroup='%s' % imagery_name, input=",".join(myInput))

    # EXPORT TIFF WITH COMPRESSION
    grass.run_command("r.out.gdal", input='%s' % imagery_name, output=folder_out+imagery_name+'_match.tiff', format='GTiff', type="Float64",
                      nodata=-1, flags='tcf', overwrite=True)  # , createopt="COMPRESS=DEFLATE,NUM_THREADS=ALL_CPUS,PREDICTOR=3,BIGTIFF=YES")

    # REMOVE ALL DATA FROM THE GRASS MAPSET TO START PROCESSING ANOTHER SCENE
    grass.run_command("g.remove", type='raster,vector',
                      pattern="%s" % date, flags='fr')
    grass.run_command("g.remove", type='group', name='%s' %
                      imagery_name, flags='f')
    name_list = []
    band_name_list = []
