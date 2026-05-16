from seed.seed_6_262 import (
    BASE,
    CODE,
    HOME,
    _exam_sol_url,
    _exam_url,
    _ps_sol_url,
    _ps_url,
)


def test_code_and_base():
    assert CODE == "MIT 6.262"
    assert BASE == (
        "https://ocw.mit.edu/courses/"
        "6-262-discrete-stochastic-processes-spring-2011"
    )
    assert HOME == BASE + "/"


def test_ps_urls_zero_pad():
    assert _ps_url(1) == BASE + "/resources/mit6_262s11_assn01/"
    assert _ps_url(12) == BASE + "/resources/mit6_262s11_assn12/"
    assert _ps_sol_url(1) == BASE + "/resources/mit6_262s11_assn01_sol/"
    assert _ps_sol_url(12) == BASE + "/resources/mit6_262s11_assn12_sol/"


def test_exam_urls():
    assert _exam_url("mid", 2011) == BASE + "/resources/mit6_262s11_mid11/"
    assert _exam_url("mid", 2010) == BASE + "/resources/mit6_262s11_mid10/"
    assert _exam_url("mid", 2009) == BASE + "/resources/mit6_262s11_mid09/"
    assert _exam_url("final", 2011) == BASE + "/resources/mit6_262s11_final11/"
    assert _exam_url("final", 2009) == BASE + "/resources/mit6_262s11_final09/"
    assert _exam_sol_url("mid", 2011) == BASE + "/resources/mit6_262s11_mid11_sol/"
    assert _exam_sol_url("final", 2011) == BASE + "/resources/mit6_262s11_final11_sol/"
