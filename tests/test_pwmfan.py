
from contextlib import ExitStack

import pytest

from afancontrol.pwmfan import PWMFan, PWMFanNorm


@pytest.fixture
def pwm_path(temp_path):
    # pwm = /sys/class/hwmon/hwmon0/pwm2
    pwm_path = temp_path / "pwm2"
    pwm_path.write_text("0\n")
    return pwm_path


@pytest.fixture
def pwm_enable_path(temp_path):
    pwm_enable_path = temp_path / "pwm2_enable"
    pwm_enable_path.write_text("0\n")
    return pwm_enable_path


@pytest.fixture
def fan_input_path(temp_path):
    # fan_input = /sys/class/hwmon/hwmon0/fan2_input
    fan_input_path = temp_path / "fan2_input"
    fan_input_path.write_text("1300\n")
    return fan_input_path


@pytest.fixture
def pwmfan(pwm_path, fan_input_path):
    return PWMFan(pwm=str(pwm_path), fan_input=str(fan_input_path))


@pytest.fixture
def pwmfan_norm(pwm_path, fan_input_path):
    return PWMFanNorm(
        pwm=str(pwm_path),
        fan_input=str(fan_input_path),
        pwm_line_start=100,
        pwm_line_end=240,
        never_stop=False,
    )


@pytest.mark.parametrize("pwmfan_fixture", ["pwmfan", "pwmfan_norm"])
def test_get_speed(pwmfan_fixture, pwmfan, pwmfan_norm, fan_input_path):
    fan = locals()[pwmfan_fixture]
    fan_input_path.write_text("721\n")
    assert 721 == fan.get_speed()


@pytest.mark.parametrize("pwmfan_fixture", ["pwmfan", "pwmfan_norm"])
@pytest.mark.parametrize("raises", [True, False])
def test_enter_exit(
    raises, pwmfan_fixture, pwmfan, pwmfan_norm, pwm_enable_path, pwm_path
):
    fan = locals()[pwmfan_fixture]

    class Exc(Exception):
        pass

    with ExitStack() as stack:
        if raises:
            stack.enter_context(pytest.raises(Exc))
        stack.enter_context(fan)

        assert "1" == pwm_enable_path.read_text()
        assert "255" == pwm_path.read_text()
        value = dict(pwmfan=100, pwmfan_norm=0.39)[pwmfan_fixture]  # 100/255 ~= 0.39
        fan.set(value)
        if raises:
            raise Exc()

    assert "0" == pwm_enable_path.read_text()
    assert "100" == pwm_path.read_text()


def test_get_set_pwmfan(pwmfan, pwm_path):
    pwmfan.set(142)
    assert "142" == pwm_path.read_text()

    pwm_path.write_text("132\n")
    assert 132 == pwmfan.get()

    pwmfan.set_full_speed()
    assert "255" == pwm_path.read_text()

    with pytest.raises(ValueError):
        pwmfan.set(256)

    with pytest.raises(ValueError):
        pwmfan.set(-1)


def test_get_set_pwmfan_norm(pwmfan_norm, pwm_path):
    pwmfan_norm.set(0.42)
    assert "101" == pwm_path.read_text()

    pwm_path.write_text("132\n")
    assert pytest.approx(0.517, 0.01) == pwmfan_norm.get()

    pwmfan_norm.set_full_speed()
    assert "255" == pwm_path.read_text()

    assert 240 == pwmfan_norm.set_norm(1.1)
    assert "240" == pwm_path.read_text()

    assert 0 == pwmfan_norm.set_norm(-0.1)
    assert "0" == pwm_path.read_text()
