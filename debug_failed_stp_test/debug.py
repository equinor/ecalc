from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay, ConvexHull
import pandas as pd
import numpy as np
import os
import sys
import scipy
print(os.getcwd())

version = scipy.__version__
print(version)

print(sys.version)

"""
For debugging functionality from the file src/libecalc/core/models/compressor/sampled/compressor_model_sampled_3d.py
"""

# qhull_points = pd.read_csv('debug/qhull_points.csv')
# chart = pd.read_csv('debug/gascompression.csv')
# x_for_interpolator = pd.read_csv('debug/x_for_interpolator.csv')

# values = pd.read_csv('debug/fuel_usage.csv')
# qhull_points = pd.read_csv('debug/kb_input/qhull_points.csv')
# x_for_interpolator = pd.read_csv('debug/kb_input/x_for_interpolator.csv')

# values = pd.read_csv('debug/kb_input/fuel_usage.csv')
# chart = pd.read_csv('debug/gascompression.csv')

# qhull_points = pd.read_csv('debug_failed_stp_test/kb_input/qhull_points.csv', header=None)
# values = pd.read_csv('debug_failed_stp_test/kb_input/fuel_usage.csv', header=None)
x_for_interpolator = pd.read_csv('debug_failed_stp_test/kb_input/x_for_interpolator.csv', header=None)

# qhull_points = pd.read_csv('debug_failed_stp_test/interpolator_input_17_09/qhull_points_17_09.csv', header=None)
# values = pd.read_csv('debug_failed_stp_test/interpolator_input_17_09/values_17.csv', header=None)
qhull_points = pd.read_csv('debug_failed_stp_test/interpolator_input_ltp_run/qhull_points_ltp_run.csv', header=None)
values = pd.read_csv('debug_failed_stp_test/interpolator_input_ltp_run/values_ltp_run.csv', header=None)


qhull_points_np = qhull_points.to_numpy()
x_for_interpolator_np = x_for_interpolator.to_numpy()
values_shape = (values.shape[0],) # values shape to match ecalc data
values_np = np.reshape(values.to_numpy(), values_shape)
# convex_hull = ConvexHull(qhull_points)
delaunay = Delaunay(qhull_points_np)

interpolator = LinearNDInterpolator(
            points=delaunay,
            values=values_np,
            fill_value=np.nan,
            rescale=False,
        )

result = interpolator(x_for_interpolator)
print(result)