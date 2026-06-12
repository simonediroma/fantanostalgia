"""
Test unitari per backend/scrapers/fbref.py

Testano solo la logica pura (algoritmo rating, mapping posizioni, parsing celle).
Nessuna richiesta HTTP — la parte di rete va testata manualmente in locale.
"""

import pytest

from backend.engine.rating import RatingWeights, compute_rating
from backend.scrapers.fbref import _int_cell, _map_position

_W = RatingWeights()  # pesi di default usati in tutti i test


def _r(**kwargs) -> float:
    """Wrapper che inietta i pesi di default."""
    return compute_rating(**kwargs, weights=_W)


# ---------------------------------------------------------------------------
# _compute_rating — casi base
# ---------------------------------------------------------------------------

def test_rating_base():
    """Giocatore neutro: 6.0"""
    r = _r(goals=0, yellow_cards=0, red_cards=0, minutes=45,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(6.0)


def test_rating_vittoria():
    r = _r(goals=0, yellow_cards=0, red_cards=0, minutes=45,
                        team_won=True, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(6.5)


def test_rating_gol():
    r = _r(goals=2, yellow_cards=0, red_cards=0, minutes=80,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(12.0)  # 6 + 3*2


def test_rating_gol_e_vittoria():
    r = _r(goals=1, yellow_cards=0, red_cards=0, minutes=90,
                        team_won=True, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(10.0)  # 6 + 0.5 vittoria + 3 gol + 0.5 (>80 min)


# ---------------------------------------------------------------------------
# _compute_rating — bonus/malus minuti
# ---------------------------------------------------------------------------

def test_rating_bonus_oltre_80_minuti():
    r = _r(goals=0, yellow_cards=0, red_cards=0, minutes=81,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(6.5)


def test_rating_nessun_bonus_80_esatti():
    """80 minuti esatti non supera soglia"""
    r = _r(goals=0, yellow_cards=0, red_cards=0, minutes=80,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(6.0)


def test_rating_malus_meno_30_minuti():
    r = _r(goals=0, yellow_cards=0, red_cards=0, minutes=15,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(5.5)


def test_rating_nessun_malus_30_esatti():
    """30 minuti esatti non scatta il malus"""
    r = _r(goals=0, yellow_cards=0, red_cards=0, minutes=30,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(6.0)


# ---------------------------------------------------------------------------
# _compute_rating — cartellini
# ---------------------------------------------------------------------------

def test_rating_giallo():
    r = _r(goals=0, yellow_cards=1, red_cards=0, minutes=60,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(5.5)


def test_rating_rosso():
    r = _r(goals=0, yellow_cards=0, red_cards=1, minutes=60,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(5.0)


def test_rating_giallo_e_rosso():
    """Doppio giallo → espulsione: si applica sia -0.5 che -1.0"""
    r = _r(goals=0, yellow_cards=1, red_cards=1, minutes=60,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(4.5)


# ---------------------------------------------------------------------------
# _compute_rating — portiere
# ---------------------------------------------------------------------------

def test_rating_portiere_clean_sheet():
    r = _r(goals=0, yellow_cards=0, red_cards=0, minutes=90,
                        team_won=False, is_goalkeeper=True, goals_conceded=0)
    assert r == pytest.approx(7.5)  # 6 + 1 clean sheet + 0.5 (>80 min)


def test_rating_portiere_un_gol_subito():
    r = _r(goals=0, yellow_cards=0, red_cards=0, minutes=90,
                        team_won=False, is_goalkeeper=True, goals_conceded=1)
    assert r == pytest.approx(5.5)  # 6 - 1 gol subito + 0.5 (>80 min)


def test_rating_portiere_tre_gol_subiti():
    r = _r(goals=0, yellow_cards=0, red_cards=0, minutes=90,
                        team_won=False, is_goalkeeper=True, goals_conceded=3)
    assert r == pytest.approx(3.5)  # 6 - 3 + 0.5


def test_rating_portiere_clean_sheet_vittoria():
    r = _r(goals=0, yellow_cards=0, red_cards=0, minutes=90,
                        team_won=True, is_goalkeeper=True, goals_conceded=0)
    assert r == pytest.approx(8.0)  # 6 + 0.5 vittoria + 1 clean sheet + 0.5 (>80 min)


# ---------------------------------------------------------------------------
# _compute_rating — combinazioni
# ---------------------------------------------------------------------------

def test_rating_attaccante_gol_vittoria_titolare():
    """Tipico attaccante che segna nella vittoria, titolare completo"""
    r = _r(goals=1, yellow_cards=0, red_cards=0, minutes=90,
                        team_won=True, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(10.0)  # 6 + 0.5 + 3 + 0.5


def test_rating_subentrante_senza_voto():
    """Subentrante con pochi minuti, nessun contributo"""
    r = _r(goals=0, yellow_cards=0, red_cards=0, minutes=10,
                        team_won=True, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(6.0)  # 6 + 0.5 vittoria - 0.5 (<30 min)


# ---------------------------------------------------------------------------
# _map_position
# ---------------------------------------------------------------------------

def test_map_gk():
    assert _map_position("GK") == "P"


def test_map_df():
    assert _map_position("DF") == "D"


def test_map_mf():
    assert _map_position("MF") == "C"


def test_map_fw():
    assert _map_position("FW") == "A"


def test_map_combined_takes_primary():
    assert _map_position("DF,MF") == "D"
    assert _map_position("MF,FW") == "C"
    assert _map_position("FW,MF") == "A"


def test_map_unknown_defaults_to_c():
    assert _map_position("") == "C"
    assert _map_position("XX") == "C"


# ---------------------------------------------------------------------------
# _int_cell
# ---------------------------------------------------------------------------

def test_int_cell_none():
    assert _int_cell(None) == 0


def test_int_cell_empty_text(mocker):
    cell = mocker.MagicMock()
    cell.get_text.return_value = ""
    assert _int_cell(cell) == 0


def test_int_cell_valid(mocker):
    cell = mocker.MagicMock()
    cell.get_text.return_value = "3"
    assert _int_cell(cell) == 3


def test_int_cell_non_numeric(mocker):
    cell = mocker.MagicMock()
    cell.get_text.return_value = "N/A"
    assert _int_cell(cell) == 0


# ---------------------------------------------------------------------------
# RatingWeights — pesi custom
# ---------------------------------------------------------------------------

def test_custom_weights_goal_bonus():
    """Con goal_bonus=5 un gol vale 5 punti invece di 3."""
    w = RatingWeights(goal_bonus=5.0)
    r = compute_rating(goals=1, yellow_cards=0, red_cards=0, minutes=60,
                       team_won=False, is_goalkeeper=False, goals_conceded=0, weights=w)
    assert r == pytest.approx(11.0)  # 6 + 5


def test_custom_weights_no_win_bonus():
    """Con win_bonus=0 la vittoria non porta punti."""
    w = RatingWeights(win_bonus=0.0)
    r = compute_rating(goals=0, yellow_cards=0, red_cards=0, minutes=60,
                       team_won=True, is_goalkeeper=False, goals_conceded=0, weights=w)
    assert r == pytest.approx(6.0)


def test_custom_weights_serialization(tmp_path):
    """to_json / from_json round-trip."""
    original = RatingWeights(goal_bonus=4.0, win_bonus=1.0)
    path = str(tmp_path / "weights.json")
    original.to_json(path)
    loaded = RatingWeights.from_json(path)
    assert loaded == original
