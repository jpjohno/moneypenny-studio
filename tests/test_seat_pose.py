from motion import direct_plan, validate_plan


def test_supported_step_preserves_side_and_is_bounded():
    plan = direct_plan('Put your left foot on the toilet seat')
    assert plan['steps'] == [{'skill': 'supported_step', 'duration': 8, 'intensity': 1, 'side': 'left'}]
    assert validate_plan({'steps': [{'skill': 'supported_step', 'duration': 900, 'side': 'right'}]})['steps'][0]['duration'] == 20
    assert direct_plan("Don't put your foot on the seat") is None
    assert direct_plan('Insert a tampon') is None


def test_bend_over_is_a_supported_direct_movement():
    assert direct_plan('Can you bend over?')['steps'][0]['skill'] == 'bend_forward'
    assert direct_plan("Don't bend over") is None
