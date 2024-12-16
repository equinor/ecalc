class ElectricityConsumer(BaseConsumer, EnergyComponent):
    component_type: Literal[
        ComponentType.COMPRESSOR,
        ComponentType.PUMP,
        ComponentType.GENERIC,
        ComponentType.PUMP_SYSTEM,
        ComponentType.COMPRESSOR_SYSTEM,
    ]
    consumes: Literal[ConsumptionType.ELECTRICITY] = ConsumptionType.ELECTRICITY
    energy_usage_model: dict[
        Period,
        ElectricEnergyUsageModel,
    ]

    _validate_el_consumer_temporal_model = field_validator("energy_usage_model")(validate_temporal_model)

    _check_model_energy_usage = field_validator("energy_usage_model")(
        lambda data: check_model_energy_usage_type(data, EnergyUsageType.POWER)
    )

    def is_fuel_consumer(self) -> bool:
        return False

    def is_electricity_consumer(self) -> bool:
        return True

    def is_provider(self) -> bool:
        return False

    def is_container(self) -> bool:
        return False

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    def evaluate_energy_usage(
        self, expression_evaluator: ExpressionEvaluator, context: ComponentEnergyContext
    ) -> dict[str, EcalcModelResult]:
        consumer_results: dict[str, EcalcModelResult] = {}
        consumer = ConsumerEnergyComponent(
            id=self.id,
            name=self.name,
            component_type=self.component_type,
            regularity=TemporalModel(self.regularity),
            consumes=self.consumes,
            energy_usage_model=TemporalModel(
                {
                    period: EnergyModelMapper.from_dto_to_domain(model)
                    for period, model in self.energy_usage_model.items()
                }
            ),
        )
        consumer_results[self.id] = consumer.evaluate(expression_evaluator=expression_evaluator)

        return consumer_results

    @field_validator("energy_usage_model", mode="before")
    @classmethod
    def check_energy_usage_model(cls, energy_usage_model):
        """
        Make sure that temporal models are converted to Period objects if they are strings
        """
        if isinstance(energy_usage_model, dict) and len(energy_usage_model.values()) > 0:
            energy_usage_model = _convert_keys_in_dictionary_from_str_to_periods(energy_usage_model)
        return energy_usage_model
