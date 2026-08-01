"""Plugin resolution tests: success paths and every failure mode."""

from __future__ import annotations

import json

import pytest

from linkdiscovery.errors import PluginError
from linkdiscovery.interfaces import RegionParser, TokenCounter
from linkdiscovery.plugins import instantiate_plugin, load_plugin
from tests.sample_plugins import (
    COUNTER_INSTANCE,
    NotAPlugin,
    SingleRegionParser,
    WordTokenCounter,
)


class TestLoadPlugin:
    def test_loads_a_class_without_instantiating(self) -> None:
        loaded = load_plugin("tests.sample_plugins:WordTokenCounter")
        assert loaded is WordTokenCounter

    def test_loads_an_instance(self) -> None:
        loaded = load_plugin("tests.sample_plugins:COUNTER_INSTANCE")
        assert isinstance(loaded, WordTokenCounter)

    def test_loads_a_function(self) -> None:
        assert load_plugin("json:dumps") is json.dumps

    @pytest.mark.parametrize(
        "spec",
        ["no-colon", "a:b:c", ":Attr", "module:", ""],
        ids=["no-colon", "two-colons", "empty-module", "empty-attr", "empty"],
    )
    def test_malformed_spec_rejected(self, spec: str) -> None:
        with pytest.raises(PluginError, match="invalid plugin spec"):
            load_plugin(spec)

    def test_missing_module_reports_module_name(self) -> None:
        with pytest.raises(PluginError, match=r"cannot import module 'nonexistent\.pkg'"):
            load_plugin("nonexistent.pkg:Thing")

    def test_import_error_is_chained(self) -> None:
        with pytest.raises(PluginError) as excinfo:
            load_plugin("nonexistent.pkg:Thing")
        assert isinstance(excinfo.value.__cause__, ImportError)

    def test_missing_attribute_reports_both_names(self) -> None:
        with pytest.raises(PluginError, match="has no attribute 'Missing'"):
            load_plugin("tests.sample_plugins:Missing")

    def test_instance_checked_against_protocol(self) -> None:
        loaded = load_plugin("tests.sample_plugins:COUNTER_INSTANCE", expected=TokenCounter)
        assert loaded.count_tokens("one two three") == 3

    def test_nonconforming_instance_rejected(self) -> None:
        with pytest.raises(PluginError, match="does not satisfy TokenCounter"):
            load_plugin("tests.sample_plugins:NOT_A_PLUGIN_INSTANCE", expected=TokenCounter)

    def test_class_against_concrete_base_uses_issubclass(self) -> None:
        with pytest.raises(PluginError, match="not a subclass of NotAPlugin"):
            load_plugin("tests.sample_plugins:WordTokenCounter", expected=NotAPlugin)

    def test_class_against_data_protocol_deferred_to_instantiation(self) -> None:
        # TokenCounter has a property member, so issubclass is impossible;
        # the class loads and the instance check happens in instantiate_plugin.
        loaded = load_plugin("tests.sample_plugins:WordTokenCounter", expected=TokenCounter)
        assert loaded is WordTokenCounter


class TestInstantiatePlugin:
    def test_instantiates_a_class(self) -> None:
        instance = instantiate_plugin("tests.sample_plugins:SingleRegionParser")
        assert isinstance(instance, SingleRegionParser)

    def test_instantiated_class_checked_against_protocol(self) -> None:
        instance = instantiate_plugin(
            "tests.sample_plugins:SingleRegionParser", expected=RegionParser
        )
        assert instance.fingerprint == "single-region-parser-v1"

    def test_nonconforming_class_rejected_after_instantiation(self) -> None:
        with pytest.raises(PluginError, match="does not satisfy RegionParser"):
            instantiate_plugin("tests.sample_plugins:NotAPlugin", expected=RegionParser)

    def test_existing_instance_returned_as_is(self) -> None:
        instance = instantiate_plugin(
            "tests.sample_plugins:COUNTER_INSTANCE", expected=TokenCounter
        )
        assert instance is COUNTER_INSTANCE

    def test_constructor_failure_reported(self) -> None:
        with pytest.raises(PluginError, match="could not be instantiated with no arguments"):
            instantiate_plugin("tests.sample_plugins:Unconstructable")
