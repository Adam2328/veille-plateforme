"""Aide ponctuelle pour renseigner les identifiants Wikidata du catalogue (hors cycle)."""
import re

# Mots attendus dans la description Wikidata (fr ou en), par type d'entité.
HINTS = {
    "company": ("entreprise", "société", "company", "groupe", "constructeur", "fabricant", "manufacturer", "corporation",
                "conglomérat", "banque", "bank", "multinational", "start-up", "startup", "laboratoire", "business"),
    "country": ("pays", "country", "état", "state", "république", "republic", "royaume", "kingdom", "territoire", "territory"),
    "org": ("organisation", "organization", "organisme", "alliance", "union", "fonds", "fund", "banque", "bank", "cour",
            "court", "agence", "agency", "groupe", "group", "mouvement", "movement", "parti", "commission", "parlement",
            "parliament", "comité", "committee", "fédération", "federation", "association", "forum", "conseil",
            "council", "institution", "régulateur", "regulator"),
    "central_bank": ("banque centrale", "central bank", "réserve", "reserve"),
    "person": ("homme", "femme", "politique", "politician", "président", "president", "entrepreneur", "businessman",
               "businesswoman", "chef", "dirigeant", "économiste", "economist", "informaticien", "computer scientist",
               "investisseur", "investor", "diplomate", "diplomat", "ministre", "minister", "ingénieur", "engineer",
               "banquier", "banker", "juriste", "lawyer", "monarque", "leader", "guide suprême", "supreme leader"),
    "player": ("joueur", "joueuse", "player", "footballeur", "footballer", "tennisman", "tennis", "basketteur",
               "basketball", "volleyeur", "volleyball"),
    "driver": ("pilote", "racing driver", "driver"),
    "team": ("club", "équipe", "team", "écurie", "franchise", "constructor"),
    "competition": ("compétition", "competition", "championnat", "championship", "tournoi", "tournament", "coupe", "cup",
                    "ligue", "league", "grand chelem", "grand slam", "jeux", "games", "course", "race", "series"),
    "crypto": ("cryptomonnaie", "cryptocurrency", "monnaie", "currency", "blockchain", "stablecoin", "jeton", "token"),
    "ai_model": ("modèle", "model", "chatbot", "agent conversationnel", "logiciel", "software", "intelligence artificielle",
                 "artificial intelligence", "assistant", "générat", "generat"),
    "index": ("indice", "index", "stock market"),
}


def pick(results: list[dict], etype: str) -> str | None:
    hints = HINTS.get(etype, ())
    return next((r["id"] for r in results if any(h in str(r.get("description", "")).lower() for h in hints)), None)


def insert_qid(text: str, eid: str, qid: str) -> str:
    return re.sub(rf"\{{id: {re.escape(eid)}, (?!wikidata)", "{id: " + eid + ", wikidata: " + qid + ", ", text, count=1)
