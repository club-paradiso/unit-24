"""Registry adapters turn an external dataset into RegistryRecord rows. Each adapter is
tied to a dated snapshot; a newer snapshot gets a new registry code so nothing is
silently overwritten."""

from radiocorpus.registry.adapters.base import RegistryAdapter, get_adapter  # noqa: F401
