import pytest

from scraping.search_sources import (
    ACTIVE_SEARCH_SOURCE_IDS,
    SEARCH_SOURCE_TYPES,
    InterparkAirSource,
    InterparkTicketSource,
    create_search_source,
)


def test_search_source_registry_includes_ticket_skeleton():
    assert InterparkAirSource.source_id in ACTIVE_SEARCH_SOURCE_IDS
    assert InterparkTicketSource.source_id not in ACTIVE_SEARCH_SOURCE_IDS
    assert InterparkAirSource.source_id in SEARCH_SOURCE_TYPES
    assert InterparkTicketSource.source_id in SEARCH_SOURCE_TYPES


def test_ticket_source_exposes_metadata_and_placeholder_contract():
    source = create_search_source(InterparkTicketSource.source_id)

    assert source.metadata["base_url"] == "https://nol.interpark.com/ticket"
    assert source.metadata["legacy_url"] == "https://tickets.interpark.com/"
    assert source.build_search_url({}) == "https://nol.interpark.com/ticket"
    with pytest.raises(NotImplementedError):
        source.search({})
