from __future__ import annotations

from planreview.services.component_model import (
    ComponentSample,
    predict_components,
    save_component_samples,
    train_component_profiles,
)


def test_component_profiles_can_be_trained_and_predicted(app_client) -> None:
    samples = [
        ComponentSample(
            label="panelboard",
            family="power-distribution",
            manufacturer="Siemens",
            source_title="Panelboard Guide",
            source_url="https://example.com/panelboard.pdf",
            page_number=1,
            text="Siemens panelboard switchboard breaker bus bar distribution panel",
        ),
        ComponentSample(
            label="elevator",
            family="vertical-transport",
            manufacturer="Otis",
            source_title="Elevator Guide",
            source_url="https://example.com/elevator.pdf",
            page_number=1,
            text="Otis elevator hoistway cab door machine room elevator modernization",
        ),
    ]
    save_component_samples(samples)
    profiles = train_component_profiles(samples)
    assert set(profiles) == {"panelboard", "elevator"}

    predictions = predict_components("distribution panelboard breaker lineup", limit=1)
    assert predictions
    assert predictions[0].label == "panelboard"
