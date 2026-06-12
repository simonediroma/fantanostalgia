"""
Algoritmo di rating storico — pesi configurabili.

I pesi hanno tutti valore positivo; il segno (+/-) è gestito
esplicitamente nella funzione compute_rating.

Uso:
    from backend.engine.rating import RatingWeights, compute_rating

    w = RatingWeights()                        # pesi di default
    w = RatingWeights.from_json("pesi.json")   # pesi da file
    w.to_json("pesi.json")                     # esporta pesi correnti
"""

import dataclasses
import json
from dataclasses import dataclass


@dataclass
class RatingWeights:
    base: float = 6.0

    # bonus
    win_bonus: float = 0.5          # squadra vince
    goal_bonus: float = 3.0         # per ogni gol segnato
    gk_clean_sheet_bonus: float = 1.0  # portiere senza gol subiti

    # malus
    gk_goal_conceded_malus: float = 1.0  # per ogni gol subito (portiere)
    yellow_card_malus: float = 0.5
    red_card_malus: float = 1.0
    long_game_bonus: float = 0.5    # minuti > 80
    short_game_malus: float = 0.5   # minuti < 30

    @classmethod
    def from_json(cls, path: str) -> "RatingWeights":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        unknown = set(data) - {f.name for f in dataclasses.fields(cls)}
        if unknown:
            raise ValueError(f"Chiavi sconosciute nel file pesi: {unknown}")
        return cls(**data)

    def to_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dataclasses.asdict(self), f, indent=2)


def compute_rating(
    *,
    goals: int,
    yellow_cards: int,
    red_cards: int,
    minutes: int,
    team_won: bool,
    is_goalkeeper: bool,
    goals_conceded: int,
    weights: RatingWeights,
) -> float:
    rating = weights.base

    if team_won:
        rating += weights.win_bonus

    rating += weights.goal_bonus * goals

    if is_goalkeeper:
        if goals_conceded == 0:
            rating += weights.gk_clean_sheet_bonus
        rating -= weights.gk_goal_conceded_malus * goals_conceded

    if minutes > 80:
        rating += weights.long_game_bonus
    if minutes < 30:
        rating -= weights.short_game_malus

    rating -= weights.yellow_card_malus * yellow_cards
    rating -= weights.red_card_malus * red_cards

    return round(rating, 1)
