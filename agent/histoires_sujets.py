"""Catalogue du compte « Histoires vraies d'argent » (06/11/2026) : articles Wikipédia en français vérifiés.

« serie » = histoire racontée en deux parties (partie 1 le soir, partie 2 le lendemain midi) ; il faut un article long.
« chiffre » = un fait frappant et sa leçon, 25 à 40 s.
Écartés à dessein : affaires politiques en cours ou personnes vivantes non condamnées, faits divers violents.
`en` = l'article anglais correspondant, pour trouver plus d'images libres (facultatif).
"""
from __future__ import annotations

_SERIES = [
    # (id, article fr, article en)
    ("humbert", "Thérèse Humbert", "Thérèse Humbert"),
    ("lustig", "Victor Lustig", "Victor Lustig"),
    ("law", "Système de Law", "Mississippi Company"),
    ("stavisky", "Affaire Stavisky", "Stavisky affair"),
    ("spaggiari", "Albert Spaggiari", "Albert Spaggiari"),
    ("meegeren", "Han van Meegeren", "Han van Meegeren"),
    ("madoff", "Bernard Madoff", "Bernie Madoff"),
    ("macgregor", "Gregor MacGregor", "Gregor MacGregor"),
    ("collier", "Affaire du collier de la reine", "Affair of the Diamond Necklace"),
    ("abagnale", "Frank Abagnale, Jr.", "Frank Abagnale"),
    ("renifleurs", "Affaire des Avions renifleurs", "Sniffer planes scandal"),
    ("hanau", "Marthe Hanau", "Marthe Hanau"),
    ("bernhard", "Opération Bernhard", "Operation Bernhard"),
    ("joconde", "Vol de La Joconde", "Mona Lisa"),
    ("fyre", "Fyre Festival", "Fyre Festival"),
    ("delvey", "Anna Delvey", "Anna Sorokin"),
    ("carbone", "Fraude à la TVA sur les quotas de carbone", None),
    ("trainpostal", "Attaque du train postal Glasgow-Londres", "Great Train Robbery (1963)"),
    ("postiches", "Gang des postiches", None),
    ("rennes", "Affaire de Rennes-le-Château", "Rennes-le-Château"),
    ("fouquet", "Nicolas Fouquet", "Nicolas Fouquet"),
    ("coeur", "Jacques Cœur", "Jacques Cœur"),
    ("holmes", "Elizabeth Holmes", "Elizabeth Holmes"),
    ("onecoin", "OneCoin", "OneCoin"),
    ("wirecard", "Wirecard", "Wirecard scandal"),
    ("kerviel", "Crise financière de janvier 2008 à la Société générale", "2008 Société Générale trading loss"),
    ("rocancourt", "Christophe Rocancourt", "Christophe Rocancourt"),
    ("oustric", "Albert Oustric", None),
    ("creditlyonnais", "Affaire du Crédit lyonnais", "Crédit Lyonnais"),
    ("beltracchi", "Wolfgang Beltracchi", "Wolfgang Beltracchi"),
    ("uniongenerale", "Union générale", "Union Générale"),
    ("empruntsrusses", "Emprunt russe", "Russian bonds"),
    ("pechiney", "Affaire Pechiney-Triangle", None),
    ("hughes", "Howard Hughes", "Howard Hughes"),
]

_CHIFFRES = [
    ("tulipes", "Tulipomanie", "Tulip mania"),
    ("ponzi", "Charles Ponzi", "Charles Ponzi"),
    ("panama", "Scandale de Panama", "Panama scandals"),
    ("krach1929", "Krach de 1929", "Wall Street crash of 1929"),
    ("weimar", "Hyperinflation de la république de Weimar", "Hyperinflation in the Weimar Republic"),
    ("mansa", "Mansa Moussa", "Mansa Musa"),
    ("rockefeller", "John Davison Rockefeller", "John D. Rockefeller"),
    ("fugger", "Jacob Fugger", "Jakob Fugger"),
    ("hetty", "Hetty Green", "Hetty Green"),
    ("kreuger", "Ivar Kreuger", "Ivar Kreuger"),
    ("leeson", "Nick Leeson", "Nick Leeson"),
    ("stanford", "Allen Stanford", "Allen Stanford"),
    ("dehory", "Elmyr de Hory", "Elmyr de Hory"),
    ("enron", "Enron", "Enron scandal"),
    ("maxwell", "Robert Maxwell", "Robert Maxwell"),
    ("belfort", "Jordan Belfort", "Jordan Belfort"),
    ("shkreli", "Martin Shkreli", "Martin Shkreli"),
    ("priam", "Trésor de Priam", "Priam's Treasure"),
    ("loewenstein", "Alfred Loewenstein", "Alfred Loewenstein"),
    ("mersud", "Compagnie de la mer du Sud", "South Sea Company"),
    ("bulleinternet", "Bulle Internet", "Dot-com bubble"),
    ("sme1992", "Crise du système monétaire européen de 1992", "Black Wednesday"),
    ("panique1907", "Panique bancaire américaine de 1907", "Panic of 1907"),
    ("subprimes", "Crise des subprimes", "Subprime mortgage crisis"),
    ("volkswagen", "Affaire Volkswagen", "Volkswagen emissions scandal"),
    ("theranos", "Theranos", "Theranos"),
    ("ignatova", "Ruja Ignatova", "Ruja Ignatova"),
]

_FORMULES = ["Énigme", "Chiffre", "Contre-pied"]


def _construire() -> list[dict]:
    sujets = []
    for format_, liste in (("serie", _SERIES), ("chiffre", _CHIFFRES)):
        for k, (id_, fr, en) in enumerate(liste):
            sujets.append({"id": id_, "article": fr, "en": en, "format": format_, "formule": _FORMULES[k % 3]})
    return sujets


CATALOGUE = _construire()
