import grass.script as grass
import glob
import os
import sys
from datetime import datetime
import time

start_tot = time.time()

# folder containing the sentinel imagery preprocessed
foldin = 'path\to\input_folder\'
# roi Shapefile
roi_in = 'path\to\roi'
res_in = 10  # GRASS Region target resolution

# BAND LIST
band_dict = {"B02": "1", "B03": "2", "B04": "3", "B05": "4", "B06": "5",
             "B07": "6", "B08": "7", "B8A": "8", "B11": "9", "B12": "10"}

# CREATE OUTPUT FOLDER WITHIN THE INPUT FOLDER
folder_out = foldin + "clipped"
if not os.path.exists(folder_out):
    os.makedirs(folder_out)

# SET REGION ACCORDING TO SHAPE AND RES
grass.run_command("v.in.ogr", input=roi_in, output="roi", overwrite=True)
grass.run_command("g.region", vect="roi", res=res_in, flags="a")

# GET DATES
data = os.listdir(foldin)
dates = []
for item in data:
    if item.endswith('.tiff'):
        date = (item.split(".")[0]).split("_")[0]
        dates.append(datetime.strptime(
            date.partition('T')[0], '%Y%m%d').date())
ldates = list(sorted(dates))
print(ldates)

# PROCESSING SCENES BY DATE
name_list = []
band_name_list = []
for d in ldates:
    start = time.time()
    for x in data:
        if x.endswith('.tiff') and x.find(d.strftime("%Y%m%d")) != -1:
            imagery_name = (x.split(".")[0]).split("_")[0]
            name_list.append(imagery_name)

            # IMPORT BANDS
            grass.run_command("r.in.gdal", input="%s" % foldin+x, output="%s" %
                              d.strftime("%Y%m%d"), flags='ok', overwrite=True)

            # CREATE GROUP
            myInput = [imagery_name + "."+band_dict.get(n) for n in band_dict]
            grass.run_command("i.group", group='%s' % imagery_name,
                              subgroup='%s' % imagery_name, input=",".join(myInput))

            grass.run_command("r.out.gdal", input='%s' % imagery_name, output='%s' %
                              folder_out+'\\'+imagery_name+'_clip.tiff', flags='tc', overwrite=True)

            # REMOVE ALL DATA FROM THE GRASS MAPSET TO START PROCESSING ANOTHER SCENE
            grass.run_command("g.remove", type='raster',
                              pattern="%s" % d.strftime("%Y%m%d"), flags='fr')
            grass.run_command("g.remove", type='group',
                              name='%s' % imagery_name, flags='f')

    end = time.time()
    print(end-start)

end_tot = time.time()
print(end_tot-start_tot)
