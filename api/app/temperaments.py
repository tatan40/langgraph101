"""Catalogue des tempéraments : libellés, descriptions envoyées à Jev (FR et EN)."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Temperament:
    id: str
    label: str
    # Description envoyée à Jev : une chaîne, ou un objet avec exemples/contre-exemples
    # pour les catégories faciles à confondre.
    fr: str | dict[str, Any]
    en: str | dict[str, Any]


TEMPERAMENTS: tuple[Temperament, ...] = (
    Temperament(
        "joyeux",
        "Heureux / enthousiaste",
        "L'auteur exprime de la joie, de l'excitation ou partage une bonne nouvelle.",
        "The author expresses joy, excitement, or shares good news.",
    ),
    Temperament(
        "reconnaissant",
        "Reconnaissant",
        "L'auteur remercie, félicite ou exprime de la gratitude, sincèrement.",
        "The author sincerely thanks, congratulates, or expresses gratitude.",
    ),
    Temperament(
        "neutre",
        "Neutre / factuel",
        "L'auteur transmet une information ou une demande sans émotion marquée.",
        "The author conveys information or a request with no marked emotion.",
    ),
    Temperament(
        "inquiet",
        "Inquiet / anxieux",
        {
            "description": "L'auteur exprime une crainte, un doute sur l'avenir ou un besoin d'être rassuré.",
            "exemple": "Je n'ai toujours pas reçu de confirmation, est-ce que ma commande a bien été prise en compte ?",
            "différence avec triste": "L'inquiétude porte sur ce qui pourrait arriver ; la tristesse sur ce qui est déjà arrivé.",
        },
        {
            "description": "The author expresses fear, doubt about what will happen, or a need for reassurance.",
            "example": "Je n'ai toujours pas reçu de confirmation, est-ce que ma commande a bien été prise en compte ?",
            "difference from sad": "Worry is about what might happen; sadness is about what already happened.",
        },
    ),
    Temperament(
        "triste",
        "Triste / déçu",
        {
            "description": "L'auteur exprime de la peine, de la déception ou du découragement, sans hostilité.",
            "exemple": "J'attendais beaucoup de ce séjour, et franchement je suis déçue.",
            "différence avec inquiet": "La tristesse porte sur ce qui est déjà arrivé ; l'inquiétude sur ce qui pourrait arriver.",
        },
        {
            "description": "The author expresses sorrow, disappointment, or discouragement, without hostility.",
            "example": "J'attendais beaucoup de ce séjour, et franchement je suis déçue.",
            "difference from worried": "Sadness is about what already happened; worry is about what might happen.",
        },
    ),
    Temperament(
        "frustre",
        "Frustré / impatient",
        {
            "description": "L'auteur est agacé par un problème qui dure, des relances ou une attente, mais reste courtois.",
            "exemple": "C'est la troisième fois que je vous écris à ce sujet, j'aimerais vraiment une solution rapide.",
            "différence avec énervé": "Pas d'attaque directe, pas d'insulte ni de majuscules : l'agacement reste contenu.",
        },
        {
            "description": "The author is annoyed by a lingering problem, repeated follow-ups, or waiting, but stays courteous.",
            "example": "C'est la troisième fois que je vous écris à ce sujet, j'aimerais vraiment une solution rapide.",
            "difference from angry": "No direct attack, insults, or shouting: the annoyance stays contained.",
        },
    ),
    Temperament(
        "enerve",
        "Énervé / en colère",
        {
            "description": "L'auteur exprime une colère explicite : reproches directs, majuscules, ponctuation excessive.",
            "exemple": "C'est INADMISSIBLE !!! Vous vous fichez complètement de vos clients.",
            "différence avec frustré": "La colère est ouverte et dirigée contre le destinataire.",
            "différence avec hostile": "Pas de menace ni d'insulte personnelle grave.",
        },
        {
            "description": "The author expresses explicit anger: direct blame, capital letters, excessive punctuation.",
            "example": "C'est INADMISSIBLE !!! Vous vous fichez complètement de vos clients.",
            "difference from frustrated": "The anger is open and aimed at the recipient.",
            "difference from hostile": "No threats or serious personal insults.",
        },
    ),
    Temperament(
        "moqueur",
        "Moqueur / sarcastique",
        {
            "description": "L'auteur utilise une ironie ou une dérision ouverte : le sens réel est l'inverse du sens littéral.",
            "exemple": "Bravo, quel service exceptionnel : seulement trois semaines pour livrer un colis.",
            "différence avec passif-agressif": "L'ironie est visible et assumée, souvent pour faire rire ou ridiculiser.",
        },
        {
            "description": "The author uses open irony or mockery: the real meaning is the opposite of the literal one.",
            "example": "Bravo, quel service exceptionnel : seulement trois semaines pour livrer un colis.",
            "difference from passive-aggressive": "The irony is visible and deliberate, often to ridicule.",
        },
    ),
    Temperament(
        "passif_agressif",
        "Passif-agressif",
        {
            "description": "L'auteur reste poli en surface mais glisse un reproche voilé.",
            "exemples": [
                "Comme déjà indiqué dans mon précédent message…",
                "Merci d'avance de bien vouloir enfin traiter ma demande.",
                "Je me permets de vous relancer, au cas où mon email se serait perdu.",
            ],
            "différence avec moqueur": "Pas d'ironie ouverte : le reproche se cache derrière les formules de politesse.",
        },
        {
            "description": "The author stays polite on the surface but slips in a veiled reproach.",
            "examples": [
                "Comme déjà indiqué dans mon précédent message…",
                "Merci d'avance de bien vouloir enfin traiter ma demande.",
                "Je me permets de vous relancer, au cas où mon email se serait perdu.",
            ],
            "difference from sarcastic": "No open irony: the reproach hides behind polite phrasing.",
        },
    ),
    Temperament(
        "hostile",
        "Hostile / menaçant",
        "L'auteur menace, insulte, pose un ultimatum ou cherche à intimider.",
        "The author threatens, insults, issues an ultimatum, or tries to intimidate.",
    ),
)

# Option de repli : uniquement dans le Choice, pas de Noul associé.
AUTRE = Temperament(
    "autre",
    "Indéterminé",
    "Aucun des tempéraments ci-dessus ne s'applique (texte vide, hors sujet, message automatique).",
    "None of the temperaments above applies (empty, off-topic, or automated message).",
)

ALL_CHOICES: tuple[Temperament, ...] = (*TEMPERAMENTS, AUTRE)
BY_ID: dict[str, Temperament] = {t.id: t for t in ALL_CHOICES}
