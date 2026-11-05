from ca.version import GENERATOR_VERSION

DATASETS = {"tuning", "final"}
_off_printed = False


class Telemetry:
    def __init__(self, client=None):
        self.client = client

    def trace_case(self, name, **kwargs):
        if self.client is None:
            return None
        return self.client.start_observation(name=name, **kwargs)

    def score(self, *args, **kwargs):
        if self.client is not None:
            return self.client.create_score(*args, **kwargs)
        return None

    def dataset_run(self, split, run_id, input, task):
        if split not in DATASETS:
            raise ValueError("dataset must be tuning or final")
        if self.client is None:
            return None
        self.client.create_dataset(name=split)
        item = self.client.create_dataset_item(dataset_name=split, input=input)
        return self.client.run_experiment(
            name=split,
            run_name=f"{GENERATOR_VERSION}:{run_id}",
            data=[item],
            task=task,
        )

    def flush(self):
        if self.client is not None:
            return self.client.flush()
        return None


def _langfuse_client(env):
    from langfuse import Langfuse

    settings = {
        "public_key": env["LANGFUSE_PUBLIC_KEY"],
        "secret_key": env["LANGFUSE_SECRET_KEY"],
    }
    if env.get("LANGFUSE_HOST"):
        settings["host"] = env["LANGFUSE_HOST"]
    return Langfuse(**settings)


def _off():
    global _off_printed
    if not _off_printed:
        print("Langfuse off")
        _off_printed = True
    return Telemetry()


def open_telemetry(env) -> Telemetry:
    if not env.get("LANGFUSE_PUBLIC_KEY") or not env.get("LANGFUSE_SECRET_KEY"):
        return _off()
    try:
        return Telemetry(_langfuse_client(env))
    except ImportError:
        return _off()
