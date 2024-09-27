from datetime import datetime

from libecalc import dto
from libecalc.common.time_utils import Period
from libecalc.expression import Expression


class TestInstallation:
    def test_valid(self, flare):
        installation_dto = dto.Installation(
            name="test",
            regularity={Period(datetime(1900, 1, 1)): Expression.setup_from_expression("sim;var")},
            hydrocarbon_export={Period(datetime(1900, 1, 1)): Expression.setup_from_expression("sim1;var1")},
            fuel_consumers=[flare],
        )
        assert installation_dto.hydrocarbon_export == {
            Period(datetime(1900, 1, 1)): Expression.setup_from_expression(value="sim1;var1"),
        }
