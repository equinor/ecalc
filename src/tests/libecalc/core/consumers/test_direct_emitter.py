from datetime import datetime

import pytest
from libecalc import dto
from libecalc.core.consumers.direct_emitter import DirectEmitter
from libecalc.dto.base import ConsumerUserDefinedCategoryType
from libecalc.expression import Expression


def test_direct_emitter(variables_map, temporal_emitter_model):
    emitter_name = "direct_emitter"
    direct_emitter = DirectEmitter(
        dto.DirectEmitter(
            name=emitter_name,
            emitter_model=temporal_emitter_model,
            user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE},
            emission_name="ch4",
            regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
        )
    )

    emissions = direct_emitter.evaluate(variables_map=variables_map)

    emissions_ch4 = emissions["ch4"]

    # Two first time steps using emitter_emission_function
    assert emissions_ch4.rate.values == pytest.approx([5.1e-06, 0.00153, 0.0033, 0.0044])
