from .dbt_generator import DbtGenerator
from .meltano_schedule_generator import MeltanoScheduleGenerator
class GeneratorFactory:

    _factory = {
        "dbt": DbtGenerator,
        "meltano_schedules": MeltanoScheduleGenerator,
    }

    @classmethod
    def get_generator(cls, generator_name):
        if generator_name in cls._factory:
            return cls._factory.get(generator_name)
        else:
            raise Exception(f"Generator type {generator_name} not found in GeneratorFactory.")
