"""Rubrique « actu » du compte Histoires vraies d'argent : chaque jour, 8 vidéos tirées de l'actualité de la veille et
du jour (flux RSS de la presse française), en plus des 2 parties de série (12 h 30 et 20 h 30) : 10 vidéos par jour.

Décisions de Stéphane du 19/11/2026 : les thèmes fixes ne marchent pas (bilan du 6 au 17/11), il faut du frais et de
l'actuel à chaque vidéo. Test dès le 20/11 : les 7 pistes et leurs 19 formats, en grille tournante sur 7 jours
(GRILLE), puis on garde les formats qui font au moins 2 fois la médiane des vues à 48 h.

Chaîne : veille() lit les flux, un seul appel Gemini choisit l'article de chaque créneau, la page de l'article est
lue (texte des paragraphes), le script est écrit sur ce texte seul (contrôle des chiffres comme les histoires), rendu
au format « programme » (60 s) ou « chiffre » (30 s), puis programmé dans Buffer par histoires.programmer.
Images : jamais de photo de presse, seulement des images libres de Wikimedia Commons (champ « recherche »).
"""
from __future__ import annotations

import email.utils
import html
import json
import re
import shutil
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import requests

from . import histoires as h
from . import programme
from .perso import MOTION, RACINE

ETAT = RACINE / "etat" / "actu.json"
NAVIGATEUR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/131 Safari/537.36", "Accept-Language": "fr-FR,fr;q=0.9"}

# flux testés le 19/11/2026 (franceinfo consommation, Ouest-France, service-public et Capital ne se lisaient pas ;
# Le Monde refuse la lecture des articles, HTTP 402)
FLUX = {
    "eco": [("franceinfo", "https://www.francetvinfo.fr/economie.rss"),
            ("20 Minutes", "https://www.20minutes.fr/feeds/rss-economie.xml"),
            ("BFM", "https://www.bfmtv.com/rss/economie/"),
            ("Le Parisien", "https://feeds.leparisien.fr/leparisien/rss/economie"),
            ("Le Figaro", "https://www.lefigaro.fr/rss/figaro_conso.xml"),
            ("Le Figaro", "https://www.lefigaro.fr/rss/figaro_economie.xml")],
    "arnaque": [("Cybermalveillance.gouv.fr", "https://www.cybermalveillance.gouv.fr/feed/atom-flux-actualites"),
                ("franceinfo", "https://www.francetvinfo.fr/internet/securite-sur-internet.rss"),
                ("20 Minutes", "https://www.20minutes.fr/feeds/rss-high-tech.xml"),
                ("Le Parisien", "https://feeds.leparisien.fr/leparisien/rss/faits-divers")],
    "justice": [("franceinfo", "https://www.francetvinfo.fr/faits-divers/justice-proces.rss"),
                ("franceinfo", "https://www.francetvinfo.fr/faits-divers.rss")],
    "politique": [("franceinfo", "https://www.francetvinfo.fr/politique.rss"),
                  ("20 Minutes", "https://www.20minutes.fr/feeds/rss-politique.xml")],
}

HEURES = ["07:30", "09:00", "10:30", "14:00", "16:30", "18:00", "19:30", "22:00"]  # 12 h 30 et 20 h 30 : la série
DEBUT_TEST = date(2026, 11, 20)
GRILLE = [  # une ligne par jour du cycle (20/11 = jour 1), un format par heure de HEURES
    ["1a", "1b", "4a", "2a", "6a", "5b", "7b", "2b"],
    ["1c", "1a", "6b", "5c", "2a", "4b", "3b", "2c"],
    ["1b", "1c", "2b", "4c", "5a", "6c", "7a", "2a"],
    ["1a", "1b", "5b", "6a", "2c", "3b", "4a", "2b"],
    ["1c", "1a", "5b", "2a", "4b", "6b", "7a", "2c"],
    ["1b", "1c", "6c", "5a", "2b", "3b", "4c", "2a"],
    ["1a", "1b", "2c", "4a", "6a", "5c", "7b", "2b"],
]

_ARNAQUE = r"arnaqu|escroq|fraud|phishing|hameçonn|faux conseiller|usurp|pirat|cyber|démarchage|faux site|spoofing"
_PROCES = r"procès|audience|tribunal|cour d'|cour de|réquisit|plaidoir|verdict|condamn|jugé|mis en examen|enquête"

# piste : groupe de flux, filtre (regex sur titre + résumé, None = tout), taille (long = 60 s, court = 30 s),
# étiquette rouge, ce que le créneau cherche (pour le choix de l'article) et la consigne d'écriture.
FORMATS: dict[str, dict] = {
    "1a": {"flux": ["eco"], "filtre": None, "taille": "long", "partie": "Actu argent",
           "cherche": "une nouvelle d'argent du jour qui change concrètement le portefeuille des Français (prix, aide, "
                      "impôt, salaire, épargne, loyer, banque, nouvelle règle)",
           "consigne": "FORMAT « CE QUE ÇA CHANGE POUR TOI » : l'accroche pose ce que le spectateur va gagner ou perdre "
                       "(« Ton *loyer* va bouger dès janvier. »). Puis : ce qui a été annoncé ou décidé, qui est "
                       "concerné, combien, à partir de quand, ce que tu dois faire ou vérifier. La scène « lecon » "
                       "dit ce qu'il faut retenir pour son argent."},
    "1b": {"flux": ["eco"], "filtre": None, "taille": "court", "partie": "Le chiffre du jour",
           "cherche": "un chiffre frappant de l'actualité économique du jour (record, hausse, baisse, montant énorme)",
           "consigne": "FORMAT « LE CHIFFRE DU JOUR » : l'accroche lâche le chiffre sans contexte (« *4,2 milliards*. "
                       "En une seule année. »). Puis : ce qu'il mesure, pourquoi il est énorme ou absurde, ce qu'il "
                       "change pour le spectateur. Une scène « chiffre » au moins. La scène « lecon » en une phrase."},
    "1c": {"flux": ["eco"], "filtre": None, "taille": "court", "partie": "Vrai ou faux",
           "cherche": "une annonce, une idée reçue ou une affirmation sur l'argent que l'article permet de vérifier",
           "consigne": "FORMAT « VRAI OU FAUX » : l'accroche pose une affirmation que beaucoup croient, en question "
                       "(« Ta banque peut bloquer ton compte sans prévenir ? *Vrai* ou faux ? »). Fais durer le "
                       "suspense deux ou trois scènes, puis la réponse avec les faits de l'article. La scène « lecon » "
                       "commence par « VRAI : » ou « FAUX : » (ou « EN PARTIE VRAI : ») suivi de la raison."},
    "2a": {"flux": ["eco", "politique"], "filtre": None, "taille": "long", "partie": "Présidentielle 2027", "lfi": True,
           "cherche": "un sujet d'actualité économique ou sociale du jour sur lequel le programme de LFI a une mesure "
                      "(choisis la fiche LFI qui y répond le mieux)",
           "consigne": "FORMAT « L'ACTU ET LE PROGRAMME » : d'abord l'actu du jour, racontée avec l'article (ce qui se "
                       "passe, les chiffres) ; puis le tournant : « Et LFI, qu'est-ce qu'elle propose ? » ; la mesure du "
                       "programme tirée de l'extrait LFI, toujours attribuée ; ce qu'elle changerait sur ce sujet. "
                       "Les chiffres de l'actu viennent de l'article, ceux de la mesure de l'extrait LFI."},
    "2b": {"flux": ["eco"], "filtre": None, "taille": "long", "partie": "Présidentielle 2027", "lfi": True,
           "cherche": "une situation du quotidien qui fait l'actualité (prix, salaire, logement, santé, études, "
                      "retraite) et la fiche LFI qui la changerait le plus pour une personne ordinaire",
           "consigne": "FORMAT « TA VIE EN 2027 SI… » : l'accroche « Et si en 2027, ton *[chose]* changeait ? » ou une "
                       "variante. Pars de la situation actuelle racontée par l'article (chiffres de l'article), puis "
                       "« Si le programme de LFI s'appliquait… » : la vie du spectateur avec la mesure, toujours au "
                       "conditionnel et attribuée (« selon LFI »). Pas de promesse à ton compte."},
    "2c": {"flux": ["politique", "eco"], "filtre": None, "taille": "long", "partie": "Présidentielle 2027", "lfi": True,
           "cherche": "un débat économique du jour où l'article rapporte les positions de plusieurs partis, "
                      "candidats ou responsables politiques",
           "consigne": "FORMAT « LES CANDIDATS FACE AU SUJET » : le sujet du jour en une scène ou deux, puis les "
                       "positions de chacun, UNIQUEMENT celles que rapporte l'article (« pour le gouvernement… », « le "
                       "RN veut… »), puis celle de LFI d'après l'extrait du programme. Chaque position est attribuée, "
                       "aucune n'est jugée ; même place pour chacun. Ne prête à personne une position absente des "
                       "sources. La scène « lecon » pose la question du choix, sans y répondre."},
    "3b": {"flux": ["eco", "justice"], "filtre": None, "taille": "long", "partie": "L'histoire se répète",
           "wiki": True,
           "cherche": "une affaire d'argent du jour (arnaque, krach, bulle, faillite, scandale, fraude) qui rappelle "
                      "une grande affaire du passé ayant un article sur Wikipédia en français (donne son titre exact)",
           "consigne": "FORMAT « L'HISTOIRE SE RÉPÈTE » : l'accroche relie les deux (« Ce qui arrive aujourd'hui est "
                       "déjà arrivé. En *1720*. »). Raconte l'affaire du jour avec l'article, puis le précédent avec "
                       "l'article Wikipédia, puis les ressemblances et la différence. La scène « lecon » : ce que "
                       "l'histoire apprend à ton argent. Les chiffres de chaque époque viennent de sa source."},
    "4a": {"flux": ["arnaque", "eco"], "filtre": _ARNAQUE, "taille": "long", "partie": "Arnaque en cours",
           "cherche": "une arnaque qui circule en ce moment en France (SMS, appel, faux site, faux conseiller, "
                      "placement), décrite par l'article",
           "consigne": "FORMAT « L'ARNAQUE DU MOMENT » : l'accroche met le spectateur dans la situation (« Ce *SMS*, tu "
                       "l'as peut-être reçu ce matin. »). Puis : comment l'arnaque se déroule, étape par étape, "
                       "combien elle a coûté (si l'article le dit), comment la reconnaître, quoi faire (ne pas "
                       "répondre, signaler, appeler sa banque au numéro habituel, si l'article le dit). La scène "
                       "« lecon » : le réflexe à garder."},
    "4b": {"flux": ["arnaque", "eco"], "filtre": _ARNAQUE, "taille": "court", "partie": "Arnaque en cours",
           "cherche": "une arnaque actuelle dont l'article donne des signes concrets pour la reconnaître",
           "consigne": "FORMAT « 3 SIGNES QUI DOIVENT T'ALERTER » : l'accroche annonce les 3 signes d'une arnaque "
                       "précise (« *3 signes* que ce conseiller est un escroc. »). Puis signe 1, signe 2, signe 3, "
                       "chacun dans une scène (« ecran » = « Signe 1 : … »), tirés de l'article. La scène « lecon » : "
                       "le réflexe à avoir."},
    "4c": {"flux": ["arnaque", "eco", "justice"], "filtre": _ARNAQUE, "taille": "long", "partie": "Arnaque en cours",
           "cherche": "un article qui raconte ce qui est arrivé à une victime d'arnaque, avec des détails concrets",
           "consigne": "FORMAT « ELLE A TOUT PERDU EN UN APPEL » : raconte l'histoire de la victime comme un récit, du "
                       "premier contact à la perte, avec les détails de l'article. La victime n'est jamais nommée : "
                       "« une retraitée de Nantes », « un étudiant », même si l'article donne son prénom. Puis comment "
                       "l'arnaque marchait et ce qui aurait dû alerter. La scène « lecon » : le réflexe à garder."},
    "5a": {"flux": ["eco"], "filtre": r"décembre|1er décembre|ce qui change|changements|au 1er|dès le 1er",
           "taille": "long", "partie": "Ce qui change",
           "cherche": "ce qui change pour l'argent des Français au 1er décembre ou dans les prochains jours (prix, "
                      "règles, aides, tarifs)",
           "consigne": "FORMAT « CE QUI CHANGE LE 1ER DÉCEMBRE » (ou à la date que donne l'article) : l'accroche sur le "
                       "changement qui touche le plus le portefeuille. Puis 3 ou 4 changements tirés de l'article, "
                       "chacun avec qui est concerné et combien. La scène « lecon » : ce qu'il faut faire avant la date."},
    "5b": {"flux": ["eco", "arnaque"], "filtre": r"black friday|soldes|promo|réduction|achats en ligne|cyber monday|"
                                                r"e-commerce|colis|livraison",
           "taille": "long", "partie": "Black Friday",
           "cherche": "le Black Friday du 27 novembre : fausses promotions, pièges, arnaques, ce que les Français "
                      "dépensent",
           "consigne": "FORMAT « BLACK FRIDAY » (vendredi 27 novembre 2026) : l'accroche sur le piège ou le chiffre le "
                       "plus fort (« Cette *promo*, elle est fausse. »). Puis ce que dit l'article : comment les prix "
                       "sont gonflés avant, les arnaques, ce que les gens dépensent, comment vérifier. La scène "
                       "« lecon » : le réflexe avant d'acheter."},
    "5c": {"flux": ["eco"], "filtre": r"noël|prime de noël|cadeaux|fêtes de fin|réveillon|jouets|sapin|budget des fêtes",
           "taille": "long", "partie": "Noël",
           "cherche": "le coût de Noël, la prime de Noël, le budget des fêtes, les prix des cadeaux ou des jouets",
           "consigne": "FORMAT « LE VRAI PRIX DE NOËL » : l'accroche sur le chiffre qui surprend (budget, hausse, "
                       "prime). Puis ce que dit l'article : combien, pour qui, quand, ce qui a changé. La scène "
                       "« lecon » : ce qu'il faut retenir pour son budget."},
    "6a": {"flux": ["eco"], "filtre": r"salaire|gagne|rémunér|revenu|smic|payé|prime|fortune|patron|footballeur|"
                                     r"milliardaire|héritage",
           "taille": "long", "partie": "Combien ça gagne",
           "cherche": "combien gagne une personne, un métier ou un dirigeant dont on parle aujourd'hui (salaire, "
                      "rémunération, prime, fortune)",
           "consigne": "FORMAT « COMBIEN IL GAGNE VRAIMENT » : l'accroche pose le montant ou la question (« Combien "
                       "gagne vraiment un *patron du CAC 40* ? »). Puis le montant de l'article, comment il se "
                       "décompose, et la comparaison avec le spectateur (le SMIC, un salaire moyen, une heure de "
                       "travail) UNIQUEMENT si l'article donne ces chiffres. La scène « lecon »."},
    "6b": {"flux": ["eco"], "filtre": r"prix|inflation|hausse|coût|cher|pouvoir d'achat|tarif|facture|baisse",
           "taille": "court", "partie": "Ton argent",
           "cherche": "une hausse ou une baisse de prix concrète (courses, énergie, loyer, carburant, transports) "
                      "chiffrée dans l'article, avec la comparaison dans le temps",
           "consigne": "FORMAT « TES 100 EUROS, AVANT ET MAINTENANT » : l'accroche sur ce que ton argent achète de moins "
                       "(ou de plus) qu'avant. Puis le prix avant, le prix maintenant, l'écart, d'après l'article "
                       "seulement (deux scènes « chiffre »). Ne calcule rien que l'article ne donne pas. La scène "
                       "« lecon »."},
    "6c": {"flux": ["eco", "justice"], "filtre": r"loto|euromillions|gagnant|jackpot|fortune|héritage|milliard|"
                                                r"faillite|ruiné|perdu|krach|bitcoin|crypto",
           "taille": "long", "partie": "Fortunes",
           "cherche": "une fortune gagnée ou perdue dont on parle aujourd'hui (gros gain au loto, héritage, faillite, "
                      "krach, cryptomonnaie)",
           "consigne": "FORMAT « FORTUNE GAGNÉE, FORTUNE PERDUE » : l'accroche sur le montant ou le retournement "
                       "(« *200 millions*. Et il a tout perdu. »). Raconte comme une histoire, avec les faits de "
                       "l'article. Un gagnant ou une personne privée n'est jamais nommé. La scène « lecon » : la leçon "
                       "d'argent ou de psychologie."},
    "7a": {"flux": ["justice"], "filtre": _PROCES, "taille": "long", "partie": "Affaire en cours",
           "cherche": "un procès ou une audience en cours sur une affaire d'argent (fraude, détournement, escroquerie, "
                      "corruption, banqueroute), avec ce qui s'est dit à l'audience",
           "consigne": "FORMAT « ÉPISODE D'AUDIENCE » : l'accroche sur le moment fort de l'audience rapporté par "
                       "l'article. Puis l'affaire en deux scènes, ce qui s'est passé à l'audience, ce que risquent les "
                       "prévenus, la suite du procès. PRÉSOMPTION D'INNOCENCE : tant qu'il n'y a pas de condamnation "
                       "définitive dans l'article, « soupçonné », « selon l'accusation », « il conteste » ; jamais "
                       "« coupable », « escroc » ou « voleur » à ton compte. La scène « lecon »."},
    "7b": {"flux": ["justice", "eco"], "filtre": _PROCES + r"|détourn|corruption|blanchi|escroquerie|fraude",
           "taille": "long", "partie": "Affaire en cours",
           "cherche": "une affaire d'argent dont parle la justice ou la presse aujourd'hui (enquête, mise en examen, "
                      "procès, condamnation), avec assez de détails pour la raconter",
           "consigne": "FORMAT « L'AFFAIRE EN 60 SECONDES » : raconte l'affaire comme une histoire, du début au point "
                       "où elle en est aujourd'hui, avec les faits de l'article. PRÉSOMPTION D'INNOCENCE : tant qu'il "
                       "n'y a pas de condamnation dans l'article, « soupçonné », « selon l'enquête », « mis en examen » ; "
                       "jamais « coupable » à ton compte ; dis où en est la procédure. La scène « lecon »."},
}

TAILLES = {  # clé de histoires.FORMATS pour le contrôle, consigne de longueur
    "long": ("actu", "LONGUEUR (45 à 60 secondes) : entre 10 et 15 scènes, de 750 à 1 100 caractères dits en tout, "
                     "question comprise (vise 900). Accroche dite : 75 caractères au plus."),
    "court": ("chiffre", "LONGUEUR (30 secondes) : entre 7 et 10 scènes, de 420 à 560 caractères dits en tout, "
                         "question comprise (vise 500). Accroche dite : 75 caractères au plus."),
}

SLOGAN = "L'actu de ton argent, décryptée chaque jour"

SYSTEME = """Tu écris le script d'une vidéo TikTok verticale pour le compte « Histoires vraies d'argent », rubrique \
actu : l'actualité de l'argent en France, celle d'aujourd'hui, expliquée à des adultes qui font défiler leur fil. Tu \
as 2 secondes pour les arrêter, puis chaque scène doit donner envie de voir la suivante.

EXACTITUDE (impératif) :
- Tes seules sources sont les textes fournis entre balises (l'article de presse, et selon le format un extrait du \
programme de LFI ou un article Wikipédia). N'invente aucun fait, aucune date, aucun montant, aucune citation.
- Ce qui vient de l'article est raconté comme un fait d'actualité ; les estimations, accusations et opinions restent \
attribuées (« selon l'enquête », « d'après l'UFC-Que Choisir », « pour le gouvernement »). Garde les « environ », \
« jusqu'à », « près de ».
- Personnes : ne nomme que les personnalités publiques (élus, ministres, dirigeants, entreprises, institutions) que \
l'article nomme. Une victime, un gagnant, un témoin ou un particulier n'est jamais nommé (« une retraitée de Lyon »).
- Justice : présomption d'innocence ; tant que l'article ne rapporte pas de condamnation, « soupçonné », « mis en \
examen », « selon l'accusation », jamais « coupable » ni « escroc » à ton compte.
- Neutre : tu expliques, tu ne milites pas, aucun appel au vote. Tout ce qui vient du programme de La France insoumise \
est attribué à LFI ou à Jean-Luc Mélenchon dans la même phrase, au conditionnel (« LFI veut… », « selon LFI… »).

ACCROCHE (première scène, type « accroche ») : selon la consigne du format ; « dit » = la même idée à l'oral. Elle \
doit faire sentir que c'est d'AUJOURD'HUI et que ça touche le spectateur.

""" + h.OUVERTURE + """

STYLE : français oral de France, présent, phrases courtes ; « tu ». Des enchaînements qui relancent (« Et c'est là que \
ça devient intéressant. », « Sauf que… », « Mais attends. »). Une relance toutes les deux ou trois scènes. Rends concret \
pour un salarié, un étudiant, un retraité, un locataire, quand l'article le permet. Pas de tiret long (—), pas d'émoji.

Scènes : une idée chacune, « dit » entre 40 et 140 caractères.
- « chiffre » : un montant ou un nombre des sources ; « grand » = ce chiffre court (« 4,2 milliards », « 1 700 € ») ; \
« ecran » = ce qu'il mesure (5 mots au plus) ;
- « date » : « grand » = la date courte ; « ecran » = ce qui se passe (5 mots au plus) ;
- « recit » : le reste ; « grand » = null sauf carte « nom » ; « ecran » = 8 mots au plus, le mot clé entre astérisques ;
- la dernière scène est de type « lecon » : ce qu'il faut retenir, en une phrase (« ecran » = cette phrase, 90 \
caractères au plus ; « dit » = la même phrase).
Au moins une scène « chiffre » ou « date ».

IMAGES : « image » = -1 pour chaque scène (aucune image n'est fournie) et « recherche » = 2 à 4 mots EN ANGLAIS pour \
trouver une photo libre sur Wikimedia Commons d'une chose réelle et visible liée à la scène (« euro banknotes », \
« supermarket France », « smartphone SMS », « Palais de justice Paris », « Assemblee nationale », « Bercy ministry »), \
jamais une idée abstraite ; deux scènes qui se suivent n'ont pas la même recherche.

« titre » : le sujet, 40 caractères au plus. « question » : une question courte, sans orienter la réponse, à laquelle \
on répond en UN mot en commentaire, et qui invite à le faire (« Ça t'est déjà arrivé ? Oui ou non, en commentaire. », \
« Normal ou scandaleux ? Dis-le en commentaire. »). Ne la mets pas dans les scènes.
« legende » : la légende, 2 à 4 lignes : l'accroche, une phrase qui donne envie, la question. Pas de hashtag ni de \
lien, pas d'émoji. « hashtags » : 3 à 5 hashtags en français sans le #."""

_ITEM = {"type": "object", "properties": {"texte": h._TXT, "valeur": h._TXT_NUL, "mauvais": {"type": "boolean"}},
         "required": ["texte", "valeur", "mauvais"], "additionalProperties": False}
_SCENE = {"type": "object", "properties": {
    "type": {"type": "string", "enum": ["accroche", "recit", "date", "chiffre", "lecon"]},
    "carte": {"type": "string", "enum": ["titre", "nom", "tampon", "chiffre", "barres", "liste", "citation", "date", "image"]},
    "ecran": h._TXT, "grand": h._TXT_NUL, "label": h._TXT_NUL, "detail": h._TXT_NUL,
    "items": {"type": "array", "items": _ITEM}, "dit": h._TXT, "accent": h._TXT,
    "source": {"type": "string", "enum": ["article", "lfi", "wikipedia"]}, "indice": {"type": "integer"},
    "image": {"type": "integer"}, "recherche": h._TXT_NUL},
    "required": ["type", "carte", "ecran", "grand", "label", "detail", "items", "dit", "accent", "source", "indice",
                 "image", "recherche"], "additionalProperties": False}
SCHEMA = {"type": "object", "properties": {
    "titre": h._TXT, "fil_titre": h._TXT, "fil": {"type": "array", "items": h._TXT},
    "scenes": {"type": "array", "items": _SCENE}, "question": h._TXT, "legende": h._TXT,
    "hashtags": {"type": "array", "items": h._TXT}},
    "required": ["titre", "fil_titre", "fil", "scenes", "question", "legende", "hashtags"], "additionalProperties": False}

# Habillage « décryptage » (motion/src/ActuReel.tsx), demandé par Stéphane le 19/11/2026 d'après des vidéos d'enquête
PRESENTATION = """PRÉSENTATION « DÉCRYPTAGE » (chaque scène est une carte plein écran sur une image ; la voix est sous-titrée \
2 ou 3 mots à la fois) :
- « carte » choisit l'affichage de la scène ; varie-les, jamais trois fois la même de suite :
  « titre » : « ecran » en capitales, court et percutant (2 à 8 mots, le mot clé entre astérisques) ; « label » = petite \
étiquette jaune au-dessus (« LA QUESTION », « CE QUI CHANGE », « LE PIÈGE »…) ou null ;
  « nom » : une personnalité, une entreprise ou une institution que l'article nomme : « ecran » = son nom, « detail » = \
son rôle (« Ministre de l'Économie »), « grand » = une date ou un fait court, ou null ;
  « tampon » : un ou deux mots qui claquent, tamponnés en travers (« FAUX », « VRAI », « INVENTÉ ? », « HASARD ? », \
« PIÈGE »), toujours justifiés par les faits ; « detail » = une ligne d'explication courte ;
  « chiffre » : « grand » = le chiffre court, « ecran » = ce qu'il mesure, « label » = étiquette au-dessus \
(« LA VRAIE RÉPONSE », « LE PRÉJUDICE ») ;
  « barres » : comparaison de 2 à 4 valeurs des sources (ce qu'on annonce / la réalité, avant / maintenant, un acteur / \
un autre) : « label » = le titre, « items » = [{texte, valeur, mauvais}], « mauvais » = true pour la valeur fausse, \
trompeuse ou qui fait mal ;
  « liste » : 2 à 5 points (signes d'arnaque, mesures, ce qui change) : « label » = le titre, « items » = [{texte (6 \
mots au plus), valeur (null ou un chiffre court), mauvais (true = à éviter, marqué d'une croix rouge)}] ;
  « citation » : une phrase réellement citée par l'article, dans « ecran » (12 mots au plus), « detail » = qui l'a \
dite et quand (« Bruno Le Maire · 2023 ») ;
  « date » : « grand » = la date (« 3 octobre 2018 »), « ecran » = ce qui s'est passé ;
  « image » : rien d'écrit, juste l'image et la voix (une ou deux fois au plus, pour respirer).
  « items » = [] pour toutes les cartes sauf « barres » et « liste ». Une scène de type « chiffre » prend la carte \
« chiffre » ou « barres » ; une scène « date » la carte « date ».
- La scène 1 (accroche) prend la carte « titre » avec un « label » (ce que c'est : « ARNAQUE EN COURS », « LE CHIFFRE \
DU JOUR », « VRAI OU FAUX ? ») et une question ou un choc en capitales (« LE SMIC : *DE COMBIEN* ? »).
- Le récit avance comme une enquête : une question posée en grand (« QUI PAIE *VRAIMENT* ? »), les éléments arrivent \
un par un, un tampon pour trancher, puis la réponse.
- « fil » : 3 à 5 mots (1 ou 2 mots chacun) qui résument les étapes ou les indices de l'enquête, dans l'ordre (« SMS », \
« LIEN », « CODE », « VIREMENT ») ; « fil_titre » = « INDICES », « ÉTAPES », « SIGNES » ou « POINTS ». « indice » de \
chaque scène = le numéro (0, 1, 2…) de l'étape du fil qu'elle révèle, ou -1 ; chaque étape est révélée une seule fois, \
dans l'ordre, et toutes le sont avant la scène « lecon ».
- « accent » : 1 à 3 mots de « dit » à mettre en jaune dans les sous-titres (ceux qui portent le sens), séparés par \
des espaces.
- « source » : d'où vient le contenu de la scène : « article », « lfi » (extrait du programme) ou « wikipedia ».
- La scène « lecon » : « label » = « À RETENIR », « LA RÉPONSE », « LE VERDICT » ou « LE RÉFLEXE »."""

_CAMPAGNE = programme._CAMPAGNE
_ATTRIBUTION = programme._ATTRIBUTION


# --------------------------------------------------------------------------- veille

def _texte(x: str | None) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", x or "")).split())


def _date(item) -> datetime | None:
    for balise in ("pubDate", "{http://www.w3.org/2005/Atom}updated", "{http://www.w3.org/2005/Atom}published",
                   "{http://purl.org/dc/elements/1.1/}date"):
        v = item.findtext(balise)
        if not v:
            continue
        try:
            d = email.utils.parsedate_to_datetime(v)
        except (TypeError, ValueError):
            try:
                d = datetime.fromisoformat(v.strip().replace("Z", "+00:00"))
            except ValueError:
                continue
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    return None


def lire_flux(groupe: str, heures: int = 72, journal=print) -> list[dict]:
    """Articles des flux du groupe publiés dans les `heures` dernières heures (ou sans date)."""
    limite = datetime.now(timezone.utc) - timedelta(hours=heures)
    articles = []
    for media, url in FLUX[groupe]:
        try:
            r = requests.get(url, headers=NAVIGATEUR, timeout=30)
            r.raise_for_status()
            racine = ElementTree.fromstring(r.content)
        except Exception as e:
            journal(f"    ⚠️ flux illisible {media} ({url}) : {type(e).__name__}")
            continue
        atom = "{http://www.w3.org/2005/Atom}"
        items = racine.findall(".//item") or racine.findall(f".//{atom}entry")
        for it in items:
            lien = it.findtext("link") or ""
            if not lien.strip():
                l = it.find(f"{atom}link")
                lien = l.get("href", "") if l is not None else ""
            titre = _texte(it.findtext("title") or it.findtext(f"{atom}title"))
            resume = _texte(it.findtext("description") or it.findtext(f"{atom}summary") or it.findtext(f"{atom}content"))
            d = _date(it)
            if not titre or not lien.strip() or (d and d < limite):
                continue
            articles.append({"media": media, "url": lien.strip(), "titre": titre, "resume": resume[:400],
                             "date": d.isoformat() if d else "", "groupe": groupe})
    return articles


def veille(journal=print) -> list[dict]:
    vus, tous = set(), []
    for groupe in FLUX:
        # une arnaque reste d'actualité une semaine ; le reste : 72 h
        for a in lire_flux(groupe, heures=168 if groupe == "arnaque" else 72, journal=journal):
            cle = a["url"].split("?")[0]
            if cle not in vus:
                vus.add(cle)
                tous.append(a)
    journal(f"📰 veille : {len(tous)} article(s) récents")
    return tous


def texte_article(url: str) -> str:
    """Texte de la page de l'article : `articleBody` des données structurées, sinon les paragraphes."""
    r = requests.get(url, headers=NAVIGATEUR, timeout=30)
    r.raise_for_status()
    page = r.text
    for m in re.finditer(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", page, re.S | re.I):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        for x in d if isinstance(d, list) else d.get("@graph", [d]) if isinstance(d, dict) else []:
            if isinstance(x, dict) and len(str(x.get("articleBody") or "")) > 600:
                return _texte(x["articleBody"])[:9000]
    paragraphes = [_texte(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", page, re.S | re.I)]
    return "\n".join(p for p in paragraphes if len(p) > 70)[:9000]


def candidats(code: str, articles: list[dict], exclus: set[str]) -> list[int]:
    f = FORMATS[code]
    idx = [k for k, a in enumerate(articles) if a["groupe"] in f["flux"] and a["url"] not in exclus]
    if f["filtre"]:
        filtres = [k for k in idx if re.search(f["filtre"], articles[k]["titre"] + " " + articles[k]["resume"], re.I)]
        idx = filtres or idx
    return idx


SCHEMA_CHOIX = {"type": "object", "properties": {"choix": {"type": "array", "items": {
    "type": "object",
    "properties": {"creneau": {"type": "integer"}, "articles": {"type": "array", "items": {"type": "integer"}},
                   "fiche": {"type": "string"}, "wikipedia": {"type": "string"}},
    "required": ["creneau", "articles", "fiche", "wikipedia"], "additionalProperties": False}}},
    "required": ["choix"], "additionalProperties": False}


def choisir(cfg: dict, codes: list[str], articles: list[dict], exclus: set[str], journal=print) -> list[dict]:
    """Un seul appel Gemini : pour chaque créneau, 3 articles classés (+ la fiche LFI ou le titre Wikipédia).
    Sans réponse : les premiers candidats de chaque créneau."""
    listes = {k: candidats(c, articles, exclus) for k, c in enumerate(codes)}
    utiles = sorted({i for v in listes.values() for i in v})
    texte = "\n".join(f"[{i}] ({articles[i]['media']}, {articles[i]['date'][:16]}) {articles[i]['titre']} : "
                      f"{articles[i]['resume'][:220]}" for i in utiles)
    creneaux = "\n".join(f"Créneau {k} : {FORMATS[c]['cherche']}. Articles possibles : "
                         f"{', '.join(map(str, listes[k][:60]))}" for k, c in enumerate(codes))
    fiches = ""
    if any(FORMATS[c].get("lfi") for c in codes):
        fiches = "\n".join(f"{f['id']} : {f['titre']}" for f in json.loads(programme.FICHES.read_text(encoding="utf-8")))
    parties = [{"text": f"<articles>\n{texte}\n</articles>"}, {"text": f"<creneaux>\n{creneaux}\n</creneaux>"}]
    if fiches:
        parties.append({"text": f"<fiches_lfi>\n{fiches}\n</fiches_lfi>"})
    systeme = ("Tu es le rédacteur en chef d'un compte TikTok sur l'argent en France. Pour chaque créneau, choisis les "
               "3 articles (numéros de sa liste) qui feraient la vidéo la plus forte : sujet frais, qui touche le "
               "portefeuille ou la curiosité du grand public, riche en faits et chiffres. Un article ne sert qu'à un "
               "créneau ; évite deux sujets proches dans la même journée ; écarte les articles réservés aux abonnés, "
               "les directs, les vidéos et les sujets trop techniques. « fiche » : pour les créneaux qui parlent de "
               "LFI, l'identifiant de la fiche LFI qui répond le mieux au sujet, sinon \"\". « wikipedia » : pour le "
               "créneau « l'histoire se répète », le titre exact d'un article de Wikipédia en français sur l'affaire "
               "passée, sinon \"\".")
    try:
        r = h._demander(cfg, parties, [], systeme=systeme, schema=SCHEMA_CHOIX, consigne="Fais les choix.")
        choix = {c["creneau"]: c for c in r.get("choix", [])}
    except Exception as e:
        journal(f"    ⚠️ choix des articles par Gemini impossible ({str(e)[:160]}) : premiers candidats")
        choix = {}
    pris: set[int] = set()
    sortie = []
    for k, c in enumerate(codes):
        ch = choix.get(k) or {}
        ordre = [i for i in ch.get("articles", []) if i in listes[k] and i not in pris]
        ordre += [i for i in listes[k] if i not in ordre and i not in pris]
        pris.update(ordre[:1])
        sortie.append({"code": c, "articles": ordre[:6], "fiche": ch.get("fiche", ""), "wikipedia": ch.get("wikipedia", "")})
    return sortie


# --------------------------------------------------------------------------- script et vidéo

def _jour_fr(jour: date) -> str:
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
            "novembre", "décembre"]
    return f"{jour.day} {mois[jour.month - 1]} {jour.year}"


def _date_courte(iso: str, jour: date) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y")
    except ValueError:
        return jour.strftime("%d/%m/%Y")


def sources(choix: dict, article: dict, texte: str, jour: date) -> tuple[list[dict], str, dict]:
    """Parties du message à Gemini, texte de contrôle des chiffres, et références pour la légende."""
    f = FORMATS[choix["code"]]
    corps = f"{article['titre']}\n{article['resume']}\n{texte}"
    parties = [{"text": f"<article media=\"{article['media']}\" date=\"{article['date'][:10]}\">\n{corps}\n</article>"}]
    controle = corps + f"\nNous sommes le {_jour_fr(jour)} ({jour.isoformat()})."
    refs: dict = {"article": article}
    if f.get("lfi"):
        fiches = json.loads(programme.FICHES.read_text(encoding="utf-8"))
        fiche = next((x for x in fiches if x["id"] == choix.get("fiche")), None)
        if fiche:
            ctx = programme._contexte(fiche)
            parties.append({"text": f"<extrait_lfi document=\"{programme.DOCS[fiche['doc']]}\" "
                                    f"mesure=\"{fiche['titre']}\">\n{ctx}\n</extrait_lfi>"})
            controle += "\n" + ctx + "\nPrésidentielle 2027 : 18 avril et 2 mai 2027."
            refs["fiche"] = fiche
        elif choix["code"] in ("2a", "2b"):
            raise RuntimeError("aucune fiche LFI choisie pour ce sujet")
    if f.get("wiki"):
        if not choix.get("wikipedia"):
            raise RuntimeError("aucun précédent Wikipédia choisi")
        w = h.article(choix["wikipedia"])
        parties.append({"text": f"<wikipedia titre=\"{w['titre']}\">\n{w['texte'][:9000]}\n</wikipedia>"})
        controle += "\n" + w["texte"]
        refs["wikipedia"] = w
    return parties, controle, refs


def reparer(script: dict) -> None:
    """Corrige sans nouvel appel ce qui faisait jeter des scripts bons (essai du 19/11/2026 : 8 refus sur 8, surtout
    une accroche dite de 81 à 88 caractères) : l'accroche dite trop longue prend le texte de sa carte ; une scène 2
    « date » devient « recit » ; sans scène « chiffre » ni « date », une carte chiffrée en devient une."""
    scenes = script.get("scenes") or []
    if not scenes:
        return
    a = scenes[0]
    ecran = re.sub(r"\*", "", a.get("ecran") or "").strip()
    if len(a.get("dit", "")) > 80 and 15 <= len(ecran) <= 80:
        a["dit"] = ecran[0].upper() + ecran[1:].lower() if ecran.isupper() else ecran
    if len(scenes) > 1 and scenes[1].get("type") == "date":
        scenes[1]["type"] = "recit"
    if not any(sc.get("type") in ("date", "chiffre") for sc in scenes):
        for sc in scenes[1:-1]:
            if sc.get("carte") in ("chiffre", "date") and (sc.get("grand") or "").strip():
                sc["type"] = sc["carte"]
                break
            valeurs = [i.get("valeur") for i in sc.get("items") or [] if i.get("valeur")]
            if sc.get("carte") == "barres" and valeurs:
                sc["type"], sc["grand"] = "chiffre", sc.get("grand") or valeurs[0]
                break


def controler(script: dict, source: str, code: str) -> list[str]:
    f = FORMATS[code]
    problemes = [p for p in h.controler(script, source, TAILLES[f["taille"]][0], 0) if "hors de la liste" not in p]
    dits = " ".join(sc.get("dit", "") for sc in script.get("scenes") or [])
    tout = " ".join([dits, script.get("legende", ""), script.get("question", "")])
    if m := _CAMPAGNE.search(tout):
        problemes.append(f"ton de campagne interdit (« {m.group(0)} ») : on explique, on ne fait pas campagne")
    if f.get("lfi") and not _ATTRIBUTION.search(dits):
        problemes.append("la voix doit attribuer la mesure à LFI au moins une fois (« LFI propose », « selon LFI »)")
    cartes = " ".join([" ".join(script.get("fil") or [])] + [" ".join([sc.get("label") or "", sc.get("detail") or ""] +
             [f"{i.get('texte', '')} {i.get('valeur') or ''}" for i in sc.get("items") or []]) for sc in script.get("scenes") or []])
    inventes = sorted(h._nombres(cartes) - h._nombres(source) - {str(n) for n in range(0, 11)})
    if inventes:
        problemes.append("chiffres des cartes absents des sources : " + ", ".join(inventes))
    scenes = script.get("scenes") or []
    if any(sc.get("carte") in ("barres", "liste") and len(sc.get("items") or []) < 2 for sc in scenes):
        problemes.append("une carte « barres » ou « liste » demande au moins 2 « items »")
    n_fil = len(script.get("fil") or [])
    if not 3 <= n_fil <= 5:
        problemes.append(f"le « fil » doit avoir 3 à 5 étapes ({n_fil})")
    elif {sc.get("indice") for sc in scenes if isinstance(sc.get("indice"), int) and sc["indice"] >= 0} != set(range(n_fil)):
        problemes.append("chaque étape du « fil » doit être révélée par une scène (« indice » 0, 1, 2…)")
    if code.startswith("7") and re.search(r"\bcoupable", tout, re.I) and not re.search(r"condamn", source, re.I):
        problemes.append("« coupable » interdit sans condamnation rapportée par l'article (présomption d'innocence)")
    return problemes


def ecrire_script(cfg: dict, code: str, parties: list[dict], controle: str, journal=print) -> dict:
    f = FORMATS[code]
    parties = parties + [{"text": PRESENTATION}, {"text": f["consigne"]},
                         {"text": TAILLES[f["taille"]][1] + " La scène 1 est TOUJOURS de type « accroche », la scène 2 "
                                  "la relance, la dernière « lecon »."}]
    remarques: list[str] = []
    for essai in range(4):
        script = h._demander(cfg, parties, remarques, systeme=SYSTEME, schema=SCHEMA)
        reparer(script)
        remarques = controler(script, controle, code)
        if not remarques:
            return script
        journal(f"    ↺ script refusé ({essai + 1}/4) : " + " ; ".join(remarques)[:300])
    raise RuntimeError("script refusé au contrôle : " + " ; ".join(remarques)[:400])


def legende(script: dict, refs: dict, images: list[dict], utilisees: set[int]) -> str:
    texte = script["legende"].replace("—", ",").strip()
    tags = [re.sub(r"\W", "", t.lstrip("#")) for t in script.get("hashtags", [])[:5]]
    tags = [t for t in tags if t]
    a = refs["article"]
    pied = f"Source : {a['media']}, « {a['titre']} » ({a['url']})."
    if refs.get("fiche"):
        fi = refs["fiche"]
        pied += f" Programme de La France insoumise, « {programme.DOCS[fi['doc']]} » ({programme._url(fi['doc'])})."
        if "presidentielle2027" not in [t.lower() for t in tags]:
            tags.append("presidentielle2027")
    if refs.get("wikipedia"):
        pied += f" Wikipédia, « {refs['wikipedia']['titre']} » (CC BY-SA)."
    credits = sorted({images[k]["credit"] for k in utilisees})
    if credits:
        pied += " Images : " + " ; ".join(credits) + "."
    if script.get("_credit_musique"):
        pied += f" Musique : {script['_credit_musique']}."
    return f"{texte}\n\n{pied}\n\n{' '.join('#' + t for t in tags)}".strip()[:2200]


def fabriquer(cfg: dict, choix: dict, articles: list[dict], jour: date, dossier_sortie: Path, nom: str,
              exclus: set[str], log=print) -> dict:
    """Une vidéo du créneau : essaie les articles choisis dans l'ordre jusqu'à un script accepté."""
    code = choix["code"]
    f = FORMATS[code]
    dossier_sortie.mkdir(parents=True, exist_ok=True)
    erreur = "aucun article candidat"
    for i in [i for i in choix["articles"] if articles[i]["url"] not in exclus][:3]:
        article = articles[i]
        log(f"    📰 {article['media']} : {article['titre'][:110]}")
        try:
            texte = texte_article(article["url"])
        except Exception as e:
            texte = ""
            log(f"    ⚠️ page illisible ({type(e).__name__}) : résumé du flux seulement")
        if len(texte) + len(article["resume"]) < 700:
            erreur = f"article trop court ({len(texte)} caractères lus)"
            log(f"    ↪ {erreur}, article suivant")
            continue
        travail = MOTION / "public" / "_histoires"
        shutil.rmtree(travail, ignore_errors=True)
        travail.mkdir(parents=True)
        try:
            parties, controle, refs = sources(choix, article, texte, jour)
            script = ecrire_script(cfg, code, parties, controle, log)
            parole = sum(len(s["dit"]) for s in script["scenes"])
            log(f"    📝 « {script['scenes'][0]['ecran']} », {len(script['scenes'])} scènes, {parole} caractères dits")
            images: list[dict] = []
            h.completer_images(script, images, travail, log)
            textes = {"article": f"{article['media']} · {_date_courte(article['date'], jour)}", "lfi": "Programme LFI 2027",
                      "wikipedia": f"Wikipédia · {(refs.get('wikipedia') or {}).get('titre', '')}"}
            for sc in script["scenes"]:
                sc["source"] = textes.get(sc.get("source") or "article", textes["article"])
                if sc.get("carte") not in ("barres", "liste"):
                    sc.pop("items", None)
            utilisees = h.rendre(cfg, {"format": "programme"}, script, images, travail, dossier_sortie / f"{nom}.mp4",
                                 dossier_sortie / f"{nom}.jpg", log, format_="programme", partie=f["partie"],
                                 slogan=SLOGAN, composition="ActuReel",
                                 extra={"fil": script.get("fil") or [], "fil_titre": script.get("fil_titre") or "Indices"})
            meta = {"format": code, "article": article, "fiche": (refs.get("fiche") or {}).get("id"),
                    "wikipedia": (refs.get("wikipedia") or {}).get("titre"),
                    "legende": legende(script, refs, images, utilisees), "script": script, "images": images}
            (dossier_sortie / f"{nom}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
            log(f"    ✅ {nom}.mp4")
            return meta
        except Exception as e:
            erreur = f"{type(e).__name__} : {str(e)[:300]}"
            log(f"    ❌ {erreur}")
            if "Gemini indisponible" in str(e):
                break  # quota épuisé : inutile d'user les autres articles
        finally:
            shutil.rmtree(travail, ignore_errors=True)
    raise RuntimeError(erreur)


# --------------------------------------------------------------------------- production quotidienne

def grille(jour: date) -> list[str]:
    return GRILLE[(jour - DEBUT_TEST).days % len(GRILLE)]


def lire_etat() -> dict:
    return json.loads(ETAT.read_text(encoding="utf-8")) if ETAT.exists() else {"faits": [], "journal": []}


def ecrire_etat(etat: dict) -> None:
    ETAT.parent.mkdir(parents=True, exist_ok=True)
    ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")


def jour_cible() -> str:
    """Jour à produire. GitHub lance les passages planifiés avec 6 à 8 h de retard (20-23/11/2026 : départ entre 9 h et
    10 h de Paris, les vidéos de 7 h 30 à 10 h 30 partaient toutes vers 11 h). Le passage part donc la veille à 15 h :
    l'après-midi on prépare le lendemain ; avant midi (retard extrême, lancement à la main) on fait le jour même."""
    maintenant = datetime.now(ZoneInfo("Europe/Paris"))
    return (maintenant.date() + timedelta(days=1 if maintenant.hour >= 12 else 0)).isoformat()


def produire(cfg: dict, log, jour: str, seulement: list[int] | None = None) -> list[dict]:
    """Fabrique les vidéos actu du `jour` dans sortie/actu/<jour>/ selon la grille du test."""
    j = date.fromisoformat(jour)
    dossier = RACINE / "sortie" / "actu" / jour
    dossier.mkdir(parents=True, exist_ok=True)
    plan_json = dossier / "plan.json"
    faites: list[dict] = json.loads(plan_json.read_text(encoding="utf-8")) if plan_json.exists() else []
    if not (cfg.get("actu") or {}).get("actif", True):
        log("ℹ️ rubrique actu désactivée (config.yaml, actu.actif)")
        plan_json.write_text(json.dumps(faites, ensure_ascii=False, indent=1), encoding="utf-8")
        return faites
    etat = lire_etat()
    codes = grille(j)
    # deux passages pour un même jour (lancement à la main + passage planifié en retard) : pas de doublon
    deja = {v["creneau"] for v in faites} | {x["creneau"] for x in etat["journal"] if x.get("jour") == jour}
    a_faire = [k for k in range(len(codes)) if k not in deja and (seulement is None or k in seulement)]
    log(f"🗓️ {jour}, jour {(j - DEBUT_TEST).days % len(GRILLE) + 1} du cycle : "
        + ", ".join(f"{HEURES[k]} {codes[k]}" for k in a_faire))
    if not a_faire:
        return faites
    articles = veille(log)
    exclus = set(etat["faits"])
    choix = choisir(cfg, [codes[k] for k in a_faire], articles, exclus, log)
    for k, ch in zip(a_faire, choix):
        meta = None
        # Créneau refusé (1 à 3 par jour du 20 au 23/11/2026) : d'abord les 3 articles suivants du même format, puis
        # le format de secours de même taille (1a long, 1b court) ; le journal garde le format réellement sorti.
        secours = "1b" if FORMATS[ch["code"]]["taille"] == "court" else "1a"
        essais = [ch, dict(ch, articles=ch["articles"][3:])]
        if ch["code"] != secours:
            essais.append({"code": secours, "articles": candidats(secours, articles, exclus)[:3], "fiche": "", "wikipedia": ""})
        for n, e in enumerate(essais):
            if not [i for i in e["articles"] if articles[i]["url"] not in exclus]:
                continue
            nom = f"actu-{jour}-{k}-{e['code']}"
            log(f"• {HEURES[k]} format {e['code']} ({FORMATS[e['code']]['partie']})" + (" — nouvel essai" if n else ""))
            try:
                meta = fabriquer(cfg, e, articles, j, dossier, nom, exclus, log)
                ch = e
                break
            except Exception as x:
                log(f"    ❌ {str(x)[:300]}")
                if "Gemini indisponible" in str(x):
                    break
        if meta is None:
            log(f"    ❌ créneau {HEURES[k]} sans vidéo")
            continue
        exclus.add(meta["article"]["url"])
        etat["faits"].append(meta["article"]["url"])
        faites.append({"nom": nom, "format": "actu", "heure": HEURES[k], "titre": meta["script"]["titre"],
                       "creneau": k, "code": ch["code"]})
        etat["journal"].append({"jour": jour, "creneau": k, "code": ch["code"], "nom": nom,
                                "url": meta["article"]["url"]})
        faites.sort(key=lambda v: v["heure"])
        plan_json.write_text(json.dumps(faites, ensure_ascii=False, indent=1), encoding="utf-8")
        ecrire_etat(etat)
        time.sleep(2)
    etat["faits"] = etat["faits"][-600:]
    ecrire_etat(etat)
    plan_json.write_text(json.dumps(faites, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"📦 {len(faites)} vidéo(s) actu sur {len(codes)} prévues le {jour}")
    return faites


def essai(cfg: dict, log, code: str) -> bool:
    """Une vidéo du format `code` dans sortie/actu-essai/, rien n'est publié ni enregistré."""
    articles = veille(log)
    ch = choisir(cfg, [code], articles, set(lire_etat()["faits"]), log)[0]
    jour = datetime.now().date()
    try:
        fabriquer(cfg, ch, articles, jour, RACINE / "sortie" / "actu-essai", f"essai-{code}", set(), log)
        return True
    except Exception as e:
        log(f"❌ {e}")
        return False


def youtube_actu(cfg: dict) -> int:
    """Vidéos actu envoyées à YouTube par jour : le total voulu moins la série, dans la limite du plafond de la chaîne."""
    a = cfg.get("actu") or {}
    direct = (cfg.get("histoires") or {}).get("youtube_direct")  # API directe : plus de plafond Buffer (2 par jour)
    total = min(int(a.get("youtube_par_jour", 5)), 6 if direct else int(a.get("youtube_plafond", 2)))
    return max(0, total - int(a.get("youtube_serie", 2)))


def programmer(cfg: dict, log, jour: str) -> bool:
    n = youtube_actu(cfg)
    log(f"▶️ YouTube : {n} vidéo(s) actu ce jour-là, TikTok : toutes")
    return h.programmer(cfg, log, jour, dossier=RACINE / "sortie" / "actu" / jour, lire=lire_etat, ecrire=ecrire_etat,
                        youtube_max=n)
