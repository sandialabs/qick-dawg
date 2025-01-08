import pytest
import sys

sys.path.append('/home/xilinx/jupyter_notebooks/qickdawg/src/')

import qickdawg as qd
import numpy as np

qd.start_client(bitfile="/home/xilinx/jupyter_notebooks/qickdawg/firmware/photon_counting/qick_4x2.bit")

@pytest.fixture
def config():
    return qd.NVConfiguration()


def test__n_initial_attributes(config):
    assert len(config.__dict__) == 6


@pytest.mark.parametrize("key, value", [
    ('ddr4', False),
    ('mr', False),
    ('n_ddr4_bins', 10),
    ('rounds', 1),
    ('reps', 1)])
def test_initial_attributes(config, key, value):
    assert config[key] == value, \
        f"Unexpected initial NVConfiguration config.{key}!={config[key]}, = {value}"


def test_time_conversion():
    config = qd.NVConfiguration()

    config.test_tus  = 1
    assert len(config.__dict__) == 9
    for key, value in {
        'test_treg': config.soccfg.us2cycles(1),
        'test_tus': config.soccfg.cycles2us(config.soccfg.us2cycles(1)),
        'test_tns': config.soccfg.cycles2us(config.soccfg.us2cycles(1)) * 1000}.items():

        assert np.isclose(config[key], value), \
           f"Unexpected config time conversion tus: {key} != {value}, == {config[key]}"

    del config
    qd.NVConfiguration()
    config = qd.NVConfiguration()
    config.test_treg = 307
    assert len(config.__dict__) == 9

    for key, value in {
        'test_treg': config.soccfg.us2cycles(1),
        'test_tus': config.soccfg.cycles2us(config.soccfg.us2cycles(1)),
        'test_tns': config.soccfg.cycles2us(config.soccfg.us2cycles(1)) * 1000}.items():

        assert np.isclose(config[key], value), \
           f"Unexpected config time conversion treg: {key} != {value}, == {config[key]}"

    del config
    qd.NVConfiguration()
    config = qd.NVConfiguration()
    config.test_tns = 1000
    assert len(config.__dict__) == 9

    for key, value in {
        'test_treg': config.soccfg.us2cycles(1),
        'test_tus': config.soccfg.cycles2us(config.soccfg.us2cycles(1)),
        'test_tns': config.soccfg.cycles2us(config.soccfg.us2cycles(1)) * 1000}.items():

        assert np.isclose(config[key], value), \
           f"Unexpected config time conversion tns: {key} != {value}, == {config[key]}"

def test_frequency_conversion():

    config = qd.NVConfiguration()
    config.test_fMHz  = 1000
    assert len(config.__dict__) == 9
    for key, value in {
        'test_freg': config.soccfg.freq2reg(1000),
        'test_fMHz': config.soccfg.reg2freq(config.soccfg.freq2reg(1000)),
        'test_fGHz': config.soccfg.reg2freq(config.soccfg.freq2reg(1000)) / 1000}.items():

        assert  np.isclose(config[key], value), \
           f"Unexpected config frequency conversion fMHz: {key} != {value}, == {config[key]}"

    config = qd.NVConfiguration()
    config.test_freg  = 873813333
    assert len(config.__dict__) == 9, \
        "Config lenght incorrect"
    for key, value in {
        'test_freg': config.soccfg.freq2reg(1000),
        'test_fMHz': config.soccfg.reg2freq(config.soccfg.freq2reg(1000)),
        'test_fGHz': config.soccfg.reg2freq(config.soccfg.freq2reg(1000)) / 1000}.items():

        assert  np.isclose(config[key], value), \
           f"Unexpected config frequency conversion freg: {key} != {value}, == {config[key]}"

    config = qd.NVConfiguration()
    config.test_fGHz = 1
    assert len(config.__dict__) == 9
    for key, value in {
        'test_freg': config.soccfg.freq2reg(1000),
        'test_fMHz': config.soccfg.reg2freq(config.soccfg.freq2reg(1000)),
        'test_fGHz': config.soccfg.reg2freq(config.soccfg.freq2reg(1000)) / 1000}.items():

        assert  np.isclose(config[key], value), \
           f"Unexpected config frequency conversion fGHz: {key} != {value}, == {config[key]}"

def test_phase_conversion():

    config = qd.NVConfiguration()
    config.test_pdegrees  = 180
    assert len(config.__dict__) == 8
    for key, value in {
        'test_preg': config.soccfg.deg2reg(180),
        'test_pdegrees': config.soccfg.reg2deg(config.soccfg.deg2reg(180))}.items():

        assert  np.isclose(config[key], value), \
           f"Unexpected config phase conversion pdeg: {key} != {value}, == {config[key]}"

    config = qd.NVConfiguration()
    config.test_preg  = 2147483648
    assert len(config.__dict__) == 8, \
        "Config lenght incorrect"
    for key, value in {
        'test_preg': config.soccfg.deg2reg(180),
        'test_pdegrees': config.soccfg.reg2deg(config.soccfg.deg2reg(180))}.items():

        assert  np.isclose(config[key], value), \
           f"Unexpected config phase conversion preg: {key} != {value}, == {config[key]}"

def test_add_linear_sweep_tus_delta():

    config = qd.NVConfiguration()
    config.add_linear_sweep('test', 'tus', 1, 11, delta=2)

    assert len(config.__dict__) == 17

    reg = config.soccfg.us2cycles(1)

    for key, value in {
        'test_start_treg': config.soccfg.us2cycles(1),
        'test_start_tus': config.soccfg.cycles2us(config.soccfg.us2cycles(1)),
        'test_start_tns': config.soccfg.cycles2us(config.soccfg.us2cycles(1)) * 1000,
        'test_end_treg': config.soccfg.us2cycles(1) * 11,
        'test_end_tus': config.soccfg.cycles2us(config.soccfg.us2cycles(1)) * 11,
        'test_end_tns': config.soccfg.cycles2us(config.soccfg.us2cycles(11)) * 11000,
        'test_delta_treg': config.soccfg.us2cycles(2),
        'test_delta_tus': config.soccfg.cycles2us(config.soccfg.us2cycles(2)),
        'test_delta_tns': config.soccfg.cycles2us(config.soccfg.us2cycles(2)) * 1000,
        'scaling_mode': 'linear',
        'nsweep_points': 6}.items():

        assert config[key] == value, \
            f"Unexpected key value for add_linear_sweep: {key} != {value}, == {config[key]}" 

def test_add_linear_sweep_tus_nsweep():

    config = qd.NVConfiguration()
    config.add_linear_sweep('test', 'tus', 1, 11, nsweep_points=6)
    assert len(config.__dict__) == 17
    reg = config.soccfg.us2cycles(1)
    for key, value in {
        'test_start_treg': config.soccfg.us2cycles(1),
        'test_start_tus': config.soccfg.cycles2us(config.soccfg.us2cycles(1)),
        'test_start_tns': config.soccfg.cycles2us(config.soccfg.us2cycles(1)) * 1000,
        'test_end_treg': config.soccfg.us2cycles(11),
        'test_end_tus': config.soccfg.cycles2us(config.soccfg.us2cycles(1)) * 11,
        'test_end_tns': config.soccfg.cycles2us(config.soccfg.us2cycles(1)) * 11000,
        'test_delta_treg': config.soccfg.us2cycles(2),
        'test_delta_tus': config.soccfg.cycles2us(config.soccfg.us2cycles(2)),
        'test_delta_tns': config.soccfg.cycles2us(config.soccfg.us2cycles(2)) * 1000,
        'scaling_mode': 'linear',
        'nsweep_points': 6}.items():

        assert config[key] == value, \
            f"Unexpected key value for add_linear_sweep: {key} != {value}, == {config[key]}" 
