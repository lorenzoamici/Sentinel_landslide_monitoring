import os
from datetime import datetime
import rasterio as rio
from skimage.exposure import match_histograms
import time

# define paths:
fold_in = "path\to\input_folder\"

# CREATE OUTPUT FOLDER WITHIN THE INPUT FOLDER
fold_out = fold_in + "hist_match\\"
if not os.path.exists(fold_out):
    os.makedirs(fold_out)

# CREATE OUTPUT FOLDER FOR TEMPORARY BANDS (later in the loop)
fold_temp = fold_in + "band_temp\\"

# GET DATES
data = os.listdir(fold_in)
dates = []
for item in data:
    if item.endswith('.tiff'):
        date = (item.split(".")[0]).split("_")[0]  # S2
        # date = item.split(".")[0] #L8
        dates.append(datetime.strptime(
            date.partition('T')[0], '%Y%m%d').date())
ldates = list(sorted(dates))
print(ldates)

# PROCESS BY DATE AND BAND
for t in range(0, len(ldates)):
    start = time.time()
    t_master = 0
    if t <= max(range(0, len(ldates))) - 1:
        d_t0 = ldates[t_master].strftime("%Y%m%d")
        d_t1 = ldates[t+1].strftime("%Y%m%d")

        # open master image - time 0
        with rio.open("%s" % fold_in+d_t0+"_clip.tiff", 'r+') as r:
            master = r.read()
            metadata_master = r.profile
            metadata_master.update(compress='deflate')

        # open slave image - time 1
        with rio.open("%s" % fold_in+d_t1+"_clip.tiff", 'r+') as s:
            slave = s.read()
            metadata_slave = s.profile
            metadata_slave.update(compress='deflate')

        # store the processed band one by one
        fold_temp_t = fold_temp+d_t1+'\\'
        if not os.path.exists(fold_temp_t):
            os.makedirs(fold_temp_t)

        # match hist of each band and store results in a new multiband raster
        for band in range(0, slave.shape[0]):

            slave_rescale = match_histograms(
                slave[band], master[band], multichannel=False)

            # Read each layer and write it to stack
            with rio.open("%s" % fold_temp_t+d_t1+"_"+str(band)+"_match.tiff", 'w', **metadata_slave) as dstBand:
                metadata_dstBand = dstBand.profile
                metadata_dstBand.update(count=1)
                dstBand.write(slave_rescale, 1)

        print("done image "+d_t1)
        end = time.time()
        print(end-start)
