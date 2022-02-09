import os
from datetime import datetime
import numpy as np
from scipy import stats
import rasterio as rio
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from windrose import WindroseAxes

fold_in_S2 = 'path\to\input_folder\'

# area
area = "ruinon"

# set acceptable error
error_threshold = 0.3
error_threshold_text = '05'

period = 'y'
master = 'fixed'

# experiment name
exp_name = '| Template = 7x7 pixels | Moving master '

# SENTINEL 2
# works with dates
data_S2 = os.listdir(fold_in_S2)
dates = []
for maps in data_S2:
    date = maps.split('.')[0].split('_')[0]+'_' + \
        maps.split('.')[0].split('_')[1]
    dates.append(date)
ldates_S2 = list(set(dates))


times = []
for t in ldates_S2:
    timeA = pd.to_datetime((t.split('_')[0]))
    timeB = pd.to_datetime((t.split('_')[1]))
    times.append(timeA)
    times.append(timeB)
    times_S2 = list(sorted(times))
start_time_S2 = times_S2[0].strftime("%Y%m%d")
end_time_S2 = times_S2[-1].strftime("%Y%m%d")

# compute variables
d_dis_S2 = []
d_dir_S2 = []
image_count_S2 = 0

pixels_above_threshold = 0
pixels_below_threshold = 0

for d in ldates_S2:
    # get mask array
    with rio.open("%s" % fold_in_S2+d+'_error.tiff', 'r+') as r:
        mask_image = r.read()
        pixels_above_threshold += (mask_image[0] > error_threshold).sum()
        pixels_below_threshold += ((mask_image[0] >= 0) & (
            mask_image[0] < error_threshold) & (mask_image[0] != np.nan)).sum()
        mask_array_inv = [mask_image[0] > error_threshold]
        mask_array = np.invert(mask_array_inv)
    # read distances and directions
    with rio.open("%s" % fold_in_S2+d+'_distance.tiff', 'r+') as p:
        dist_image = p.read()
        # mask distances
    dist_image[0][mask_array[0] == False] = np.nan
    dist_image[0][dist_image[0] == -1] = np.nan
    # read distances and directions
    with rio.open("%s" % fold_in_S2+d+'_direction.tiff', 'r+') as s:
        dir_image = s.read()
    # mask directions
    dir_image[0][mask_array[0] == False] = np.nan
    dir_image[0][dir_image[0] == -1] = np.nan
    # Create dune distance and direction variables and plot them
    d_dis_S2.append(dist_image[0].flatten()[
                    np.logical_not(np.isnan(dist_image[0].flatten()))]*10)
    d_dir_S2.append(dir_image[0].flatten()[
                    np.logical_not(np.isnan(dir_image[0].flatten()))])

    image_count_S2 += 1

dist_array_S2 = np.concatenate(d_dis_S2, axis=0)
dir_array_S2 = np.concatenate(d_dir_S2, axis=0)
# invert direction to correct the mistake (to be investigated)
# dir_array_S2_inv =  np.where(dir_array_S2 <= 180.0, dir_array_S2+180.0, dir_array_S2-180.0)

n_of_pixels_S2 = int(dir_image[0].shape[0]*dir_image[0].shape[1])
n_of_changes_S2 = int(dist_array_S2.shape[0])
textstr = '\n'.join((
    r'$error-level=%.2f$' % (error_threshold, ),
    r'$T_{start}=%s$' % (start_time_S2, ),
    r'$T_{end}=%s$' % (end_time_S2, )))

print("Pixels above threshold: " + str(pixels_above_threshold))
print("Pixels below threshold: " + str(pixels_below_threshold))
print("Total pixels: " + str(pixels_above_threshold + pixels_below_threshold))


# Plot distance and direction variables
ax = WindroseAxes.from_ax()
ax.set_xticklabels(['E', 'N-E', 'N', 'N-W', 'W', 'S-W', 'S', 'S-E'])
# ax.bar(dir_array_S2_inv, dist_array_S2, normed=True, opening=0.8, edgecolor='white')
ax.bar(dir_array_S2, dist_array_S2, normed=True,
       opening=0.8, edgecolor='white')  # nsector=16
# ax.set_title(exp_name +
# '| n. of scenes = '+str(image_count_S2))
ax.set_legend(title="Displacement [m]", bbox_to_anchor=(
    1, 0), loc="lower right", bbox_transform=plt.gcf().transFigure)
# these are matplotlib.patch.Patch properties
props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
# place a text box in upper left in axes coords
ax.text(0.0, 0.95, textstr, transform=ax.transAxes, fontsize=10,
        verticalalignment='bottom', bbox=props)
# plt.savefig(fold_out+period+'_'+master+'_windrose.png')
