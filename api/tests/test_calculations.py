from app import calculations as calc


def test_edge_bps():
    assert calc.edge_bps(5700, 4400) == 1300


def test_no_expected_value():
    assert calc.expected_value_bps("NO", 3500, 5200) == 1300


def test_brier_scores():
    outcome, user, market, improvement = calc.brier_scores_bps_squared(7000, 5500, "YES")
    assert outcome == 10000
    assert user == 9_000_000
    assert market == 20_250_000
    assert improvement == 11_250_000


def test_buy_cost_with_fees():
    assert calc.buy_cost_minor_units(20, 4000, 12) == 812


def test_sell_proceeds_with_fees():
    assert calc.sell_proceeds_minor_units(10, 6500, 8) == 642

