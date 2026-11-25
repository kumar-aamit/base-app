import pytest

from baseapp.appspec import AppSpec, AppSpecError, load_app_spec


def write(tmp_path, text):
    (tmp_path / "app.yaml").write_text(text)
    return tmp_path


def test_missing_file_gives_placeholder_defaults(tmp_path):
    assert load_app_spec(tmp_path) == AppSpec()


def test_empty_file_gives_defaults(tmp_path):
    assert load_app_spec(write(tmp_path, "")) == AppSpec()


def test_reads_alert_triage(tmp_path):
    spec = load_app_spec(write(tmp_path,
        'name: Alert Triage\nmark: shield\nbrand: "#1D4ED8"\nsite: HQ data center\nscreens: [triage]\n'))
    assert spec.name == "Alert Triage" and spec.brand == "#1D4ED8"
    assert spec.site == "HQ data center" and spec.screens == ("triage",)
    assert spec.mark_icon == "shield"


def test_malformed_yaml_names_the_line(tmp_path):
    with pytest.raises(AppSpecError, match=r"app/app.yaml: line 2"):
        load_app_spec(write(tmp_path, "name: A\nbrand: [\n"))


def test_bad_brand_names_field_and_fix(tmp_path):
    with pytest.raises(AppSpecError, match=r'brand "blue" is not valid; use a hex color like "#1D4ED8"'):
        load_app_spec(write(tmp_path, "brand: blue\n"))


def test_unknown_key_is_an_error(tmp_path):
    with pytest.raises(AppSpecError, match=r'unknown field "colour"'):
        load_app_spec(write(tmp_path, "colour: red\n"))
