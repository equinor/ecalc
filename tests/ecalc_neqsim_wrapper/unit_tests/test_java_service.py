import pytest

from ecalc_neqsim_wrapper.java_service import (
    NeqsimJPypeService,
    NeqsimPy4JService,
    NeqsimService,
    ProgrammingError,
    Py4JConfig,
)


@pytest.fixture
def neqsim_module(with_neqsim_service):
    yield with_neqsim_service.get_neqsim_module()


def test_py4j_service(neqsim_module):
    """Testing the most simple case to ensure that the java service is running and working."""
    thermo_system = neqsim_module.thermo.system.SystemSrkEos(280.0, 10.0)
    thermo_system.addComponent("methane", 10.0)
    thermo_system.addComponent("water", 4.0)

    thermo_dynamic_operations = neqsim_module.thermodynamicoperations.ThermodynamicOperations(thermo_system)
    thermo_dynamic_operations.TPflash()

    gas_enthalpy = thermo_system.getPhase(0).getEnthalpy()

    thermo_system.initPhysicalProperties("Viscosity")
    gas_viscosity = thermo_system.getPhase(0).getViscosity("kg/msec")

    assert gas_enthalpy
    assert gas_viscosity


def test_get_new_py4j_instance():
    """
    Default, and set in conftest.py is to use Py4J implementation.
    Returns:

    """
    neqsim_service = NeqsimService.instance()
    assert isinstance(neqsim_service, NeqsimPy4JService)


def test_same_instance():
    neqsim_service = NeqsimService.instance()
    neqsim_service_2 = NeqsimService.instance()
    assert neqsim_service is neqsim_service_2


def test_init_not_allowed():
    with pytest.raises(ProgrammingError):
        NeqsimJPypeService()


def test_reinitialize_not_allowed():
    # We have already set jpype=False in the conftest fixture, not allowed to change!
    with pytest.raises(ProgrammingError):
        NeqsimService.factory(use_jpype=True).initialize()


class TestPy4JConfig:
    """Tests for Py4JConfig dataclass."""

    def test_default_values(self):
        config = Py4JConfig()
        assert config.maximum_memory == "2G"
        assert config.shutdown_on_exit is True

    def test_custom_values(self):
        config = Py4JConfig(maximum_memory="1G", shutdown_on_exit=False)
        assert config.maximum_memory == "1G"
        assert config.shutdown_on_exit is False

    def test_immutable(self):
        config = Py4JConfig()
        with pytest.raises(AttributeError):
            config.maximum_memory = "4G"  # type: ignore[misc]

    def test_invalid_memory_format_raises(self):
        with pytest.raises(ValueError, match="Invalid maximum_memory"):
            Py4JConfig(maximum_memory="2gb")

    def test_invalid_memory_no_unit_raises(self):
        with pytest.raises(ValueError, match="Invalid maximum_memory"):
            Py4JConfig(maximum_memory="2048")

    def test_valid_memory_formats(self):
        assert Py4JConfig(maximum_memory="512M").maximum_memory == "512M"
        assert Py4JConfig(maximum_memory="2g").maximum_memory == "2g"
        assert Py4JConfig(maximum_memory="4096m").maximum_memory == "4096m"
        assert Py4JConfig(maximum_memory="1T").maximum_memory == "1T"


class TestConfigurePy4J:
    """Tests for NeqsimService.configure_py4j()."""

    def test_configure_after_initialize_raises(self):
        """configure_py4j called after initialize() raises RuntimeError."""
        # The autouse fixture already initialized the service
        with pytest.raises(RuntimeError, match="must be called before"):
            NeqsimService.configure_py4j(Py4JConfig())

    def test_default_config_used_when_not_configured(self):
        """Without configure_py4j(), default Py4JConfig is used."""
        service = NeqsimService.instance()
        assert isinstance(service, NeqsimPy4JService)
        assert service._config.maximum_memory == "2G"
        assert service._config.shutdown_on_exit is True

    def test_reset_clears_config(self):
        """reset_py4j_config() clears the stored config."""
        NeqsimService.reset_py4j_config()
        assert NeqsimService._py4j_config is None


class TestPy4JShutdownOnExit:
    """Tests for shutdown_on_exit and Py4JConfig lifecycle behavior.

    These tests call shutdown() directly instead of relying on `with` statement __exit__,
    because the session-scoped fixture in tests/conftest.py patches __exit__ to a no-op
    for the entire test session (to keep the JVM alive across tests).
    """

    @pytest.fixture(autouse=True)
    def _manage_lifecycle(self, with_neqsim_service):
        """Shut down the fixture's service so these tests can manage their own lifecycle."""
        with_neqsim_service.shutdown()
        NeqsimService.reset_py4j_config()
        yield
        import ecalc_neqsim_wrapper.java_service as js

        service = js._neqsim_service
        if (
            service is not None
            and isinstance(service, NeqsimPy4JService)
            and getattr(service, "_gateway", None) is not None
        ):
            service.shutdown()
        NeqsimService.reset_py4j_config()

    def test_shutdown_on_exit_false_config(self):
        """With shutdown_on_exit=False, service stays alive after shutdown is skipped."""
        import ecalc_neqsim_wrapper.java_service as js

        NeqsimService.configure_py4j(Py4JConfig(shutdown_on_exit=False))
        service = NeqsimService.factory(use_jpype=False).initialize()
        assert service._config.shutdown_on_exit is False
        pid = service._gateway.java_process.pid

        # Service is alive
        assert js._neqsim_service is not None
        assert js._neqsim_service._gateway is not None
        assert js._neqsim_service._gateway.java_process.pid == pid

    def test_configure_py4j_custom_memory_is_applied(self):
        """Custom maximum_memory from configure_py4j propagates to the service."""
        NeqsimService.configure_py4j(Py4JConfig(maximum_memory="1G"))
        service = NeqsimService.factory(use_jpype=False).initialize()
        assert service._config.maximum_memory == "1G"

    def test_shutdown_clears_service_and_double_shutdown_is_safe(self):
        """shutdown() clears the global service and can be called twice without raising."""
        import ecalc_neqsim_wrapper.java_service as js

        service = NeqsimService.factory(use_jpype=False).initialize()
        assert js._neqsim_service is not None

        service.shutdown()
        assert js._neqsim_service is None

        service.shutdown()  # second call should not raise
