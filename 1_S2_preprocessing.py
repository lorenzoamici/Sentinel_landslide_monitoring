import grass.script as grass
import glob
import os
import sys
from datetime import datetime
import time

start = time.time()

# folder containing the sentinel imagery .SAFE
foldin = 'path\to\input_folder'
# roi Shapefile
roi_in = 'path\to\roi'
res_in = 10  # GRASS Region target resolution

# BAND LIST
band_list = ["B02", "B03", "B04", "B05",
             "B06", "B07", "B08", "B8A", "B11", "B12"]

# CREATE OUTPUT FOLDER WITHIN THE INPUT FOLDER
folder_out = foldin + '\\' + "outDOS"
if not os.path.exists(folder_out):
    os.makedirs(folder_out)

# SET REGION ACCORDING TO SHAPE AND RES
grass.run_command("v.in.ogr", input=roi_in, output="roi", overwrite=True)
grass.run_command("g.region", vector="roi", res=res_in, flags="a")

# GET DATES
data = os.listdir(foldin)
dates = []
for item in data:
    if item.endswith('.SAFE'):
        date = (item.split("_")[-1]).split(".SAFE")[0]
        dates.append(datetime.strptime(
            date.partition('T')[0], '%Y%m%d').date())
ldates = list(set(dates))

# PROCESSING SCENES BY DATE
name_list = []
band_name_list = []
for d in ldates:
    for x in data:
        if x.endswith('.SAFE') and x.find(d.strftime("%Y%m%d")) != -1:
            name_list.append(x.split("_")[5]+"_"+x.split("_")[2])

            # IMPORT BANDS (flag -c to import vector cloud mask).
            grass.run_command("i.sentinel.import", input=foldin +
                              '\\'+x, flags="cr", overwrite=True)

            # CLOUD MASKING
            cloud_mask_name_original = x.split(
                '_')[4]+'_'+x.split('_')[1]+'_MSK_CLOUDS'
            cloud_mask_name = x.split("_")[5]+"_"+x.split("_")[2]+'_MSK_CLOUDS'
            cloud_check = grass.read_command("g.list", flags="f", type="vect")
            if cloud_mask_name_original in cloud_check:
                grass.run_command("g.rename", vector="%s,%s" %
                                  (cloud_mask_name_original, cloud_mask_name))
                grass.run_command("v.to.rast", input="%s" % cloud_mask_name, output="%s" %
                                  cloud_mask_name+'_rast', use='val', overwrite=True)
                grass.run_command("g.remove", type='vector',
                                  pattern="%s" % d.strftime("%Y%m%d"), flags='fr')
                for u in band_list:
                    band = x.split("_")[5]+"_"+x.split("_")[2]+'_'+u
                    grass.mapcalc("$new = if (isnull($cloudmask)== 1, $original, null())", new="%s" %
                                  band+'_cf', cloudmask="%s" % cloud_mask_name+'_rast', original="%s" % band, overwrite=True)
            else:
                for u in band_list:
                    band = x.split("_")[5]+"_"+x.split("_")[2]+'_'+u
                    grass.run_command("g.rename", rast="%s,%s" %
                                      (band, band+'_cf'))

    # MERGE SAME BANDS OF MULTIPLE TILES AND CORRECT WITH DOS
    for n in band_list:
        band_name_list = [s + "_"+n+'_cf' for s in name_list]

        if len(name_list) > 1:
            # PATCH BANDS
            grass.run_command("r.patch", input="%s" % ",".join(
                band_name_list), output=d.strftime("%Y%m%d")+"_"+n+'_cf', overwrite=True)
        else:
            # SINGLE IMAGERY SCENE, RENAME ONLY WITHOUT PATCHING
            grass.run_command("g.rename", rast="%s,%s" % (
                band_name_list[0], d.strftime("%Y%m%d")+"_"+n+'_cf'))
        # GET MINIMUM VALUE OF PATCHED BANDS
        vmin = float(grass.parse_command('r.univar', map='%s' %
                                         d.strftime("%Y%m%d")+"_"+n+'_cf', flags='g')['min'])
        # COMPUTE DOS
        grass.mapcalc("$new = $original - $minimum", new=d.strftime("%Y%m%d")+"_dos_"+n,
                      original=d.strftime("%Y%m%d")+"_"+n+'_cf', minimum=vmin, overwrite=True)

    # CREATE GROUP
    name = d.strftime("%Y%m%d")+"_dos"
    myInput = [name + "_"+n for n in band_list]
    grass.run_command("i.group", group='s2', input=",".join(myInput))

    # EXPORT TIFF WITH COMPRESSION
    grass.run_command("r.out.gdal", input='s2', output=folder_out +
                      "\\" + name+'.tiff', flags='tc', overwrite=True)

    # REMOVE ALL DATA FROM THE GRASS MAPSET TO START PROCESSING ANOTHER SCENE
    grass.run_command("g.remove", type='raster,vector',
                      pattern="%s" % d.strftime("%Y%m%d"), flags='fr')
    grass.run_command("g.remove", type='group', name='s2', flags='f')
    name_list = []
    band_name_list = []

end = time.time()
print(end-start)
