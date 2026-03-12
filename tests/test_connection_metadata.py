from ael.connection_metadata import (
    validate_bench_connections,
    validate_bench_setup,
    validate_connection_metadata,
    validate_default_wiring,
    validate_verification_views,
)


def test_validate_default_wiring_rejects_empty_values():
    errors = validate_default_wiring({"swd": "P3", "verify": ""})
    assert errors == ["default_wiring[verify] must be a non-empty string"]


def test_validate_bench_connections_rejects_missing_from_and_to():
    errors = validate_bench_connections([{"from": "PA4"}, {"to": "P0.0"}])
    assert "bench_connections[0].to is required" in errors
    assert "bench_connections[1].from is required" in errors


def test_validate_verification_views_requires_pin_and_resolved_target():
    errors = validate_verification_views({"signal": {"pin": "sig"}, "led": {"resolved_to": "P0.3"}})
    assert "verification_views[signal].resolved_to is required" in errors
    assert "verification_views[led].pin is required" in errors


def test_validate_bench_setup_requires_expected_shapes():
    errors = validate_bench_setup(
        {
            "dut_to_instrument": [{"inst_gpio": 11}],
            "dut_to_instrument_analog": [{"dut_signal": "3V3"}],
            "serial_console": {"baud": 115200},
            "instrument_roles": [{"role": "uart_instrument"}],
            "external_inputs": [{"kind": "analog_in"}],
            "peripheral_signals": [{"role": "SPI0_SCK"}],
            "ground_required": "yes",
            "ground_confirmed": "yes",
        }
    )
    assert "bench_setup.dut_to_instrument[0].dut_gpio is required" in errors
    assert "bench_setup.dut_to_instrument_analog[0].inst_adc_gpio is required" in errors
    assert "bench_setup.serial_console.port is required" in errors
    assert "bench_setup.instrument_roles[0].instrument_id is required" in errors
    assert "bench_setup.external_inputs[0].dut_signal is required" in errors
    assert "bench_setup.peripheral_signals[0].dut_signal is required" in errors
    assert "bench_setup.ground_required must be a boolean" in errors
    assert "bench_setup.ground_confirmed must be a boolean" in errors


def test_validate_connection_metadata_accepts_live_meter_shape():
    errors = validate_connection_metadata(
        {"observe_map": {"sig": "P0.0"}},
        {
            "bench_setup": {
                "dut_to_instrument": [{"dut_gpio": "X1(GPIO4)", "inst_gpio": 11, "expect": "toggle"}],
                "serial_console": {"port": "auto_usb_serial_jtag", "baud": 115200},
                "peripheral_signals": [{"role": "ADC1_CH0", "dut_signal": "GPIO0/ADC1_CH0"}],
                "external_inputs": [{"source": "UNSPECIFIED_ANALOG_SOURCE", "dut_signal": "GPIO0/ADC1_CH0", "kind": "analog_in"}],
                "ground_required": True,
                "ground_confirmed": True,
            }
        },
    )
    assert errors == []
