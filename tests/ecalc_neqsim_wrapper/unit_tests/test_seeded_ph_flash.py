from __future__ import annotations

from ecalc_neqsim_wrapper.cache_service import CacheService
from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService
from libecalc.process.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.process.fluid_stream.fluid_properties import FluidProperties


class FakeNeqsimFluid:
    def __init__(self, name: str, calls: list[tuple[str, float, float, str]]) -> None:
        self.name = name
        self.calls = calls

    def set_new_pressure_and_temperature(
        self,
        new_pressure_bara: float,
        new_temperature_kelvin: float,
    ) -> FakeNeqsimFluid:
        self.calls.append(("tp", new_pressure_bara, new_temperature_kelvin, self.name))
        return FakeNeqsimFluid("temperature_seeded", self.calls)

    def set_new_pressure_and_enthalpy(
        self,
        new_pressure: float,
        new_enthalpy_joule_per_kg: float,
    ) -> FakeNeqsimFluid:
        self.calls.append(("ph", new_pressure, new_enthalpy_joule_per_kg, self.name))
        return FakeNeqsimFluid(f"ph_from_{self.name}", self.calls)


def test_temperature_guess_preconditions_ph_flash_and_populates_target_cache(monkeypatch):
    NeqSimFluidService.reset_instance()
    CacheService.clear_all()
    CacheService._caches.clear()
    service = NeqSimFluidService.instance()

    calls: list[tuple[str, float, float, str]] = []
    reference_fluid = FakeNeqsimFluid("reference", calls)
    fluid_model = FluidModel(composition=FluidComposition(methane=1.0), eos_model=EoSModel.PR)

    monkeypatch.setattr(service, "_get_reference_fluid", lambda fluid_model: reference_fluid)

    def extract_properties(neqsim_fluid: FakeNeqsimFluid, fluid_model: FluidModel) -> FluidProperties:
        return FluidProperties(
            temperature_kelvin=310.0 if neqsim_fluid.name == "ph_from_temperature_seeded" else 288.15,
            pressure_bara=50.0,
            density=1.0,
            enthalpy_joule_per_kg=1_000.0,
            z=0.9,
            kappa=1.2,
            vapor_fraction_molar=1.0,
            molar_mass=fluid_model.composition.molar_mass_mixture,
            standard_density=0.7,
        )

    monkeypatch.setattr(service, "_extract_properties", extract_properties)

    seeded = service.flash_ph(
        fluid_model=fluid_model,
        pressure_bara=50.0,
        target_enthalpy=1_000.0,
        temperature_guess_kelvin=310.0,
    )
    cached_unseeded = service.flash_ph(
        fluid_model=fluid_model,
        pressure_bara=50.0,
        target_enthalpy=1_000.0,
    )

    assert seeded.temperature_kelvin == 310.0
    assert cached_unseeded == seeded
    assert calls == [
        ("tp", 50.0, 310.0, "reference"),
        ("ph", 50.0, 1_000.0, "temperature_seeded"),
    ]
