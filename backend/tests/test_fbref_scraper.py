"""
Test unitari per backend/scrapers/fbref.py

Testano solo la logica pura (algoritmo rating, mapping posizioni, parsing celle).
Nessuna richiesta HTTP — la parte di rete va testata manualmente in locale.
"""

import pytest

from backend.scrapers.fbref import _compute_rating, _int_cell, _map_position


# ---------------------------------------------------------------------------
# _compute_rating — casi base
# ---------------------------------------------------------------------------

def test_rating_base():
    """Giocatore neutro: 6.0"""
    r = _compute_rating(goals=0, yellow_cards=0, red_cards=0, minutes=45,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(6.0)


def test_rating_vittoria():
    r = _compute_rating(goals=0, yellow_cards=0, red_cards=0, minutes=45,
                        team_won=True, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(6.5)


def test_rating_gol():
    r = _compute_rating(goals=2, yellow_cards=0, red_cards=0, minutes=80,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(12.0)  # 6 + 3*2


def test_rating_gol_e_vittoria():
    r = _compute_rating(goals=1, yellow_cards=0, red_cards=0, minutes=90,
                        team_won=True, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(10.0)  # 6 + 0.5 vittoria + 3 gol + 0.5 (>80 min)


# ---------------------------------------------------------------------------
# _compute_rating — bonus/malus minuti
# ---------------------------------------------------------------------------

def test_rating_bonus_oltre_80_minuti():
    r = _compute_rating(goals=0, yellow_cards=0, red_cards=0, minutes=81,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(6.5)


def test_rating_nessun_bonus_80_esatti():
    """80 minuti esatti non supera soglia"""
    r = _compute_rating(goals=0, yellow_cards=0, red_cards=0, minutes=80,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(6.0)


def test_rating_malus_meno_30_minuti():
    r = _compute_rating(goals=0, yellow_cards=0, red_cards=0, minutes=15,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(5.5)


def test_rating_nessun_malus_30_esatti():
    """30 minuti esatti non scatta il malus"""
    r = _compute_rating(goals=0, yellow_cards=0, red_cards=0, minutes=30,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(6.0)


# ---------------------------------------------------------------------------
# _compute_rating — cartellini
# ---------------------------------------------------------------------------

def test_rating_giallo():
    r = _compute_rating(goals=0, yellow_cards=1, red_cards=0, minutes=60,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(5.5)


def test_rating_rosso():
    r = _compute_rating(goals=0, yellow_cards=0, red_cards=1, minutes=60,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(5.0)


def test_rating_giallo_e_rosso():
    """Doppio giallo → espulsione: si applica sia -0.5 che -1.0"""
    r = _compute_rating(goals=0, yellow_cards=1, red_cards=1, minutes=60,
                        team_won=False, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(4.5)


# ---------------------------------------------------------------------------
# _compute_rating — portiere
# ---------------------------------------------------------------------------

def test_rating_portiere_clean_sheet():
    r = _compute_rating(goals=0, yellow_cards=0, red_cards=0, minutes=90,
                        team_won=False, is_goalkeeper=True, goals_conceded=0)
    assert r == pytest.approx(7.5)  # 6 + 1 clean sheet + 0.5 (>80 min)


def test_rating_portiere_un_gol_subito():
    r = _compute_rating(goals=0, yellow_cards=0, red_cards=0, minutes=90,
                        team_won=False, is_goalkeeper=True, goals_conceded=1)
    assert r == pytest.approx(5.5)  # 6 - 1 gol subito + 0.5 (>80 min)


def test_rating_portiere_tre_gol_subiti():
    r = _compute_rating(goals=0, yellow_cards=0, red_cards=0, minutes=90,
                        team_won=False, is_goalkeeper=True, goals_conceded=3)
    assert r == pytest.approx(3.5)  # 6 - 3 + 0.5


def test_rating_portiere_clean_sheet_vittoria():
    r = _compute_rating(goals=0, yellow_cards=0, red_cards=0, minutes=90,
                        team_won=True, is_goalkeeper=True, goals_conceded=0)
    assert r == pytest.approx(8.0)  # 6 + 0.5 vittoria + 1 clean sheet + 0.5 (>80 min)


# ---------------------------------------------------------------------------
# _compute_rating — combinazioni
# ---------------------------------------------------------------------------

def test_rating_attaccante_gol_vittoria_titolare():
    """Tipico attaccante che segna nella vittoria, titolare completo"""
    r = _compute_rating(goals=1, yellow_cards=0, red_cards=0, minutes=90,
                        team_won=True, is_goalkeeper=False, goals_conceded=0)
    assert r == pytest.approx(10.0)  # 6 + 0.5 + 3 + 0.5


def test_rating_subentrante_senza_voto():
    """Subentrante con pochi minuti, nessun contributo"""
    r = _compute_rating(goals=0, yellow_cards=0, red_cards=0, minutes=10,
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
