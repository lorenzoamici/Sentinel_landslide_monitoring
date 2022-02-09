import time
from scipy.spatial import distance
from skimage.feature import match_template
from skimage.feature import register_translation  # deprecated
from skimage.registration import phase_cross_correlation
import rasterio as rio
import fiona
import rasterio.mask
import numpy as np
from datetime import datetime
import os
import math

# from: https://www.analytics-link.com/single-post/2018/08/21/Calculating-the-compass-direction-between-two-points-in-Python


def angle_between(p1, p2):
    deg = math.atan2(p2[1]-p1[1], p2[0]-p1[0])/math.pi*180
    if deg < 0:
        deg_compass = 360 + deg
    else:
        deg_compass = deg
    return deg_compass


# define template size S2
row_offset_up = 3
row_offset_down = 4
col_offset_left = 3
col_offset_right = 4


# define step size for moving template
row_step = 1
col_step = 1

# define paths:
fold_in_master = 'path\to\input_folder\'
fold_in_slave = 'path\to\input_folder\'
fold_out = 'path\to\output_folder' + \
    str(row_offset_down+row_offset_up) + 'x' + \
    str(col_offset_left+col_offset_right) + '\\'
if not os.path.exists(fold_out):
    os.makedirs(fold_out)

fold_mask = fold_out+"\\masked\\"
if not os.path.exists(fold_mask):
    os.makedirs(fold_mask)

# GET DATES
data = os.listdir(fold_in_master)
dates = []
for item in data:
    if item.endswith('.tiff'):
        date = (item.split(".")[0]).split("_")[0]
        print(date)
        dates.append(datetime.strptime(
            date.partition('T')[0], '%Y%m%d').date())
ldates = list(sorted(dates))
print(ldates)

t_master = ldates[0]

for t in range(0, len(ldates)):
    start = time.time()
    if t <= max(range(0, len(ldates))) - 1:
        d_t0 = ldates[t].strftime("%Y%m%d")  # moving master
        # d_t0 = t_master.strftime("%Y%m%d") # fixed master
        d_t1 = ldates[t+1].strftime("%Y%m%d")

        # open master image - time 0
        with rio.open("%s" % fold_in_master+d_t0+"_match.tiff", 'r+') as r:
            master = r.read()
            metadata_master = r.profile
            metadata_master.update(dtype=rio.float64, count=1)

        # open slave image - time 1
        with rio.open("%s" % fold_in_slave+d_t1+"_match.tiff", 'r+') as r:
            slave = r.read()
            metadata_slave = r.profile
            metadata_slave.update(dtype=rio.float64, count=1)

        # define template centres iteratively
        row_middles_list = list(
            np.arange(row_offset_up*2, master[0].shape[0]-row_offset_down*2, row_step))
        col_middles_list = list(
            np.arange(col_offset_left*2, master[0].shape[1]-col_offset_right*2, col_step))

        # initialize 2darray that contain the new raster bands with matching results
        distance_array = np.empty((master[0].shape[0], master[0].shape[1]))
        distance_array[:] = np.nan
        direction_array = np.empty((master[0].shape[0], master[0].shape[1]))
        direction_array[:] = np.nan
        rms_error_array = np.empty((master[0].shape[0], master[0].shape[1]))
        rms_error_array[:] = np.nan
        rho_array = np.empty((master[0].shape[0], master[0].shape[1]))
        rho_array[:] = np.nan

        for row_middle in row_middles_list:
            for col_middle in col_middles_list:

                if master[0][row_middle, col_middle] != 0:
                    # template on the master image
                    tmpl_row_up = row_middle - row_offset_up
                    tmpl_row_down = row_middle + row_offset_down
                    tmpl_col_left = col_middle - col_offset_left
                    tmpl_col_right = col_middle + col_offset_right

                    template = master[0][tmpl_row_up: tmpl_row_down,
                                         tmpl_col_left: tmpl_col_right]

                    # template on the slave image
                    offset_template = slave[0][tmpl_row_up: tmpl_row_down,
                                               tmpl_col_left: tmpl_col_right]

                    # cross correlation
                    shift, error, diffphase = phase_cross_correlation(
                        template, offset_template, upsample_factor=1, space='real')

                    if shift[0] != 0.0 or shift[1] != 0.0:

                        mcorr_offset_template = slave[0][tmpl_row_up+int(shift[0]): tmpl_row_down+int(
                            shift[0]), tmpl_col_left+int(shift[1]): tmpl_col_right+int(shift[1])]

                        # compute distance and direction of the template translation
                        centre = np.array((row_middle, col_middle))
                        match = np.array(
                            (row_middle + shift[0], col_middle + shift[1]))
                        dist = round(distance.euclidean(centre, match), 3)

                        # store change vectors distances, directions, errors and max norm xcorr coeff (rho) in 2d array
                        distance_array[row_middle, col_middle] = dist
                        direction = round(angle_between(centre, match), 2)
                        direction_array[row_middle, col_middle] = direction
                        rms_error_array[row_middle, col_middle] = error
                        rho = match_template(mcorr_offset_template, template)
                        rho_array[row_middle, col_middle] = rho[0][0]

            if row_middle in list(np.arange(1000, 11000, 1000)):
                print(str(row_middle))

        with fiona.open("path\to\mask", "r") as shapefile:
            shapes = [feature["geometry"] for feature in shapefile]

        with rio.open('%s' % fold_out+d_t0+"_"+d_t1+"_distance.tiff", 'w', **metadata_slave) as dst1:
            dst1.write(distance_array, 1)

        with rio.open('%s' % fold_out+d_t0+"_"+d_t1+"_direction.tiff", 'w', **metadata_slave) as dst2:
            dst2.write(direction_array, 1)

        with rio.open('%s' % fold_out+d_t0+"_"+d_t1+"_error.tiff", 'w', **metadata_slave) as dst3:
            dst3.write(rms_error_array, 1)

        with rio.open('%s' % fold_out+d_t0+"_"+d_t1+"_rho.tiff", 'w', **metadata_slave) as dst4:
            dst4.write(rho_array, 1)

        with rasterio.open('%s' % fold_out+d_t0+"_"+d_t1+"_distance.tiff") as src1:
            out_image1, out_transform1 = rasterio.mask.mask(
                src1, shapes, crop=True)
            out_meta1 = src1.meta

        out_meta1.update({"driver": "GTiff",
                          "height": out_image1.shape[1],
                          "width": out_image1.shape[2],
                          "transform": out_transform1})

        with rasterio.open('%s' % fold_mask+d_t0+"_"+d_t1+"_distance.tiff", "w", **out_meta1) as dest1:
            dest1.write(out_image1)

        with rasterio.open('%s' % fold_out+d_t0+"_"+d_t1+"_direction.tiff") as src2:
            out_image2, out_transform2 = rasterio.mask.mask(
                src2, shapes, crop=True)
            out_meta2 = src2.meta

        out_meta2.update({"driver": "GTiff",
                          "height": out_image2.shape[1],
                          "width": out_image2.shape[2],
                          "transform": out_transform2})

        with rasterio.open('%s' % fold_mask+d_t0+"_"+d_t1+"_direction.tiff", "w", **out_meta2) as dest2:
            dest2.write(out_image2)

        with rasterio.open('%s' % fold_out+d_t0+"_"+d_t1+"_error.tiff") as src3:
            out_image3, out_transform3 = rasterio.mask.mask(
                src3, shapes, crop=True)
            out_meta3 = src3.meta

        out_meta3.update({"driver": "GTiff",
                          "height": out_image3.shape[1],
                          "width": out_image3.shape[2],
                          "transform": out_transform3})

        with rasterio.open('%s' % fold_mask+d_t0+"_"+d_t1+"_error.tiff", "w", **out_meta3) as dest3:
            dest3.write(out_image3)

        with rasterio.open('%s' % fold_out+d_t0+"_"+d_t1+"_distance.tiff") as src4:
            out_image4, out_transform4 = rasterio.mask.mask(
                src4, shapes, crop=True)
            out_meta4 = src4.meta

        out_meta4.update({"driver": "GTiff",
                          "height": out_image4.shape[1],
                          "width": out_image4.shape[2],
                          "transform": out_transform4})

        with rasterio.open('%s' % fold_mask+d_t0+"_"+d_t1+"_rho.tiff", "w", **out_meta4) as dest4:
            dest4.write(out_image4)

        print('done with '+d_t0+'-'+d_t1)
        end = time.time()
        print(end-start)
