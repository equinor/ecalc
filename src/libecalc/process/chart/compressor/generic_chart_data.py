"""Generic chart curves in simplified compressor model.

For now, only chart 105 and 75 is used, save all for possible use later. E.g. if extending to variable efficiency
model.

From the calculated rates, find the maximum(actual) rate. Then put the design point such that this maximum is just
covered by the maximum at the reference point
"""

import numpy as np

UNIFIED_GENERIC_CHART_CURVE_DATA_105 = np.asarray(
    [
        [0.878913798, 1.289869247],
        [0.929112832, 1.271644457],
        [0.97269818, 1.247344747],  # Points at which rate~=1 - reference point for max head scaling factor
        [1.038726745, 1.200770298],  # Points at which rate~=1 - reference point for max head scaling factor
        [1.099463139, 1.148120922],
        [1.158871891, 1.089396618],
        [1.231463064, 0.99827269],  # Point at which head=1 - reference point for max rate scaling factor
        [1.278951663, 0.913223698],
        [1.323778851, 0.809949924],
    ]
)


UNIFIED_GENERIC_CHART_CURVE_DATA_98 = np.asarray(
    [
        [0.7809284, 1.129882353],
        [0.815887574, 1.122103203],
        [0.857308136, 1.100710544],
        [0.916847818, 1.067649164],
        [0.998369841, 1.001526411],
        [1.077293694, 0.927624501],
        [1.140672571, 0.84983302],
        [1.183332159, 0.773986328],
        [1.218229271, 0.705918786],
    ]
)
UNIFIED_CHART_CURVE_DATA_75 = np.asarray(
    [
        [0.498902665, 0.558852888],
        [0.529285159, 0.546703033],
        [0.553058057, 0.5325282],
        [0.612499498, 0.506203512],
        [0.667962103, 0.46570399],
        [0.70889013, 0.427229447],
        [0.730015921, 0.409004665],
    ]
)


UNIFIED_GENERIC_CHART_CURVE_MAXIMUM_SPEED_RATES = UNIFIED_GENERIC_CHART_CURVE_DATA_105[:, 0]
UNIFIED_GENERIC_CHART_CURVE_MAXIMUM_SPEED_HEADS = UNIFIED_GENERIC_CHART_CURVE_DATA_105[:, 1]
UNIFIED_GENERIC_CHART_CURVE_MINIMUM_SPEED_RATES = UNIFIED_CHART_CURVE_DATA_75[:, 0]
UNIFIED_GENERIC_CHART_CURVE_MINIMUM_SPEED_HEADS = UNIFIED_CHART_CURVE_DATA_75[:, 1]
