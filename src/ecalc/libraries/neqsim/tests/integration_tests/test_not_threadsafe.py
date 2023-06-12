from threading import Thread

import pytest
from neqsim_ecalc_wrapper import start_server

"""
A small test class showing that NeqSim is currently not thread-safe

Ie. 2 threads working towards the same gateway, interchangely changing a fluid-setting
will interfere with each other
"""

java_gateway = start_server()


def thread_job(has_water: bool):
    neqsim = java_gateway.jvm.neqsim
    Fluid = neqsim.thermo.Fluid()

    assert Fluid.isHasWater() is not has_water
    Fluid.setHasWater(has_water)


@pytest.mark.xfail(reason="No longer a static variable in NeqSim, could remove test if not new case found")
def test_run_neqsim_in_2_threads():
    neqsim = java_gateway.jvm.neqsim
    # Initially, has water is false
    Fluid = neqsim.thermo.Fluid()
    assert Fluid.isHasWater() is False  # default

    # set to true in separate thread
    new_thread_has_water = Thread(target=thread_job, args=(True,))
    new_thread_has_water.start()
    new_thread_has_water.join()

    assert Fluid.isHasWater() is True

    # set to false in separate thread
    new_thread_has_not_water = Thread(target=thread_job, args=(False,))
    new_thread_has_not_water.start()
    new_thread_has_not_water.join()

    assert Fluid.isHasWater() is False
