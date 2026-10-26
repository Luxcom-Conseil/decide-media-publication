"""Catalogue des sujets des Reels « conseils et astuces psychologiques » du compte Instagram de Stéphane.

Adapté du skill marketing-psychology de Corey Haines (github.com/coreyhaines31/marketingskills, licence MIT) :
chaque modèle mental y est repris en français, tourné vers la vie de tous les jours et le travail, avec l'astuce
pratique. C'est la seule source de faits du Reel : Gemini met en forme, il n'ajoute ni étude, ni chiffre, ni chercheur.
"""
from __future__ import annotations

CATEGORIES = {
    "cerveau": "Les pièges du cerveau",
    "influence": "Influence et persuasion",
    "action": "Passer à l'action",
    "penser": "Penser mieux",
    "argent": "Psychologie de l'argent",
    "reussir": "Réussir sur la durée",
}

# (id, catégorie, nom, l'idée, l'astuce)
SUJETS: list[tuple[str, str, str, str, str]] = [
    # --- les pièges du cerveau
    ("attribution", "cerveau", "L'erreur fondamentale d'attribution",
     "On explique le comportement des autres par leur caractère, et rarement par leur situation. « Il est en retard parce qu'il "
     "est désorganisé », alors qu'il était peut-être bloqué par la circulation.",
     "Avant de juger quelqu'un, cherche d'abord ce qui, dans sa situation, a pu le pousser à agir ainsi. Le problème est "
     "souvent dans le contexte, pas dans la personne."),
    ("exposition", "cerveau", "L'effet de simple exposition",
     "On aime davantage ce qu'on a déjà vu. La familiarité crée la préférence, même sans qu'on s'en rende compte.",
     "Pour te faire connaître, la régularité compte plus qu'un coup d'éclat. Et quand tu préfères une marque, demande-toi si "
     "c'est la meilleure ou juste la plus vue."),
    ("disponibilite", "cerveau", "L'heuristique de disponibilité",
     "On juge qu'une chose est fréquente quand des exemples nous viennent facilement à l'esprit. Ce qui est récent ou "
     "spectaculaire paraît plus courant qu'il ne l'est.",
     "Quand une peur ou une envie te semble évidente, cherche les vrais chiffres avant de décider. Et pour convaincre, raconte "
     "un exemple concret : il marque plus qu'une statistique."),
    ("confirmation", "cerveau", "Le biais de confirmation",
     "On cherche les informations qui confirment ce qu'on pense déjà, et on ignore celles qui le contredisent.",
     "Avant une décision importante, cherche volontairement trois arguments contre ton idée. Et pour convaincre quelqu'un, "
     "pars de ce qu'il croit déjà au lieu de l'attaquer de front."),
    ("lindy", "cerveau", "L'effet Lindy",
     "Plus une idée ou une pratique a duré, plus elle a de chances de durer encore. Les vieilles idées survivent souvent aux "
     "nouvelles modes.",
     "Avant de tout changer pour une nouveauté, vérifie que tu gardes les bases qui ont fait leurs preuves."),
    ("mimetique", "cerveau", "Le désir mimétique",
     "On désire une chose parce que d'autres la désirent. L'envie se transmet comme une contagion.",
     "Avant d'acheter, demande-toi si tu veux vraiment cette chose ou si tu veux ce que les autres ont. Et sache qu'une file "
     "d'attente donne envie d'entrer."),
    ("sunk_cost", "cerveau", "Le piège des coûts irrécupérables",
     "On continue d'investir dans un projet parce qu'on y a déjà mis beaucoup, même quand ce n'est plus raisonnable.",
     "Pose-toi une seule question : si je partais de zéro aujourd'hui, est-ce que je choisirais encore ça ? Ce que tu as déjà "
     "dépensé ne doit pas décider à ta place."),
    ("possession", "cerveau", "L'effet de possession",
     "On accorde plus de valeur à une chose dès qu'on la possède.",
     "C'est pour ça que les essais gratuits marchent si bien. Avant de garder un abonnement après l'essai, demande-toi si tu "
     "l'achèterais aujourd'hui."),
    ("ikea", "cerveau", "L'effet IKEA",
     "On accorde plus de valeur à ce qu'on a construit soi-même, même imparfait.",
     "Pour qu'une équipe ou un client tienne à un projet, fais-le participer à sa construction. Et méfie-toi de ton attachement "
     "à tes propres idées."),
    ("gratuit", "cerveau", "L'effet du prix zéro",
     "Gratuit n'est pas seulement un prix bas : c'est un déclencheur à part, qui nous fait faire des choix peu rationnels.",
     "Devant un « offert », demande-toi ce que tu donnes en échange : ton temps, tes données ou un achat que tu n'avais pas "
     "prévu."),
    ("present", "cerveau", "Le biais du présent",
     "On préfère fortement une récompense immédiate à une récompense future, même plus grande.",
     "Pour tenir un objectif, donne-toi une petite récompense tout de suite. Pour convaincre, montre ce que la personne gagne "
     "dès aujourd'hui."),
    ("statu_quo", "cerveau", "Le biais du statu quo",
     "On préfère que les choses restent comme elles sont. Changer demande un effort et paraît risqué.",
     "Si tu veux faire changer quelqu'un d'habitude, rends le changement facile et rassurant. Et demande-toi si tu gardes "
     "quelque chose par choix ou par habitude."),
    ("defaut", "cerveau", "L'effet de l'option par défaut",
     "On accepte très souvent l'option déjà cochée. Le choix par défaut est puissant.",
     "Relis toujours les cases déjà cochées avant de valider. Et dans ta vie, fais de la bonne habitude l'option par défaut."),
    ("paradoxe_choix", "cerveau", "Le paradoxe du choix",
     "Trop d'options nous paralysent. Moins de choix mène souvent à plus de décisions.",
     "Quand tu proposes quelque chose, limite-toi à trois options et recommande-en une. Quand tu bloques sur un choix, "
     "élimine d'abord les options qui ne te conviennent pas."),
    ("gradient", "cerveau", "L'effet de gradient d'objectif",
     "Plus on se rapproche d'un but, plus on accélère l'effort. Voir sa progression motive.",
     "Découpe tes objectifs en étapes visibles et coche-les. Une barre de progression qui avance donne envie de finir."),
    ("pic_fin", "cerveau", "La règle du pic et de la fin",
     "On juge une expérience surtout sur son moment le plus fort et sur sa fin, pas sur sa moyenne.",
     "Soigne la fin d'un rendez-vous, d'un événement ou d'un service. C'est elle dont on se souviendra."),
    ("zeigarnik", "cerveau", "L'effet Zeigarnik",
     "Une tâche inachevée occupe plus l'esprit qu'une tâche terminée. Une boucle ouverte crée une tension.",
     "Pour te remettre au travail, commence juste la tâche : ton esprit voudra la finir. Et note ce qui reste à faire pour "
     "libérer ta tête le soir."),
    ("pratfall", "cerveau", "L'effet de la gaffe",
     "Une personne compétente devient plus sympathique quand elle montre un petit défaut. La perfection rapproche moins.",
     "N'aie pas peur d'avouer une petite faiblesse. « Je ne suis pas le moins cher, mais… » inspire souvent plus confiance."),
    ("malediction", "cerveau", "La malédiction du savoir",
     "Quand on sait quelque chose, on n'arrive plus à imaginer ce que c'est de ne pas le savoir. Les experts expliquent mal "
     "aux débutants.",
     "Fais relire ton message par quelqu'un qui ne connaît pas ton domaine. S'il ne comprend pas, ce n'est pas lui le problème."),
    ("regret", "cerveau", "L'aversion au regret",
     "On évite les décisions qui pourraient nous faire regretter, même quand elles sont probablement bonnes.",
     "Pour rassurer quelqu'un qui hésite, enlève le risque du regret : un essai, une garantie, une sortie facile."),
    ("preuve_sociale", "cerveau", "La preuve sociale",
     "On suit ce que font les autres. Ce qui est populaire paraît bon et sûr.",
     "Un avis client vaut souvent plus qu'un long argument. Mais devant la foule, demande-toi si elle a raison ou si elle suit "
     "juste les autres."),
    # --- influence et persuasion
    ("reciprocite", "influence", "La réciprocité",
     "Quand on reçoit, on se sent obligé de rendre. Donner en premier crée l'envie de donner en retour.",
     "Donne de la valeur avant de demander quoi que ce soit. Et quand on t'offre quelque chose, tu as le droit de dire non "
     "quand même."),
    ("engagement", "influence", "L'engagement et la cohérence",
     "Une fois qu'on s'est engagé, même un peu, on veut rester cohérent avec ce choix.",
     "Pour avancer, demande d'abord un petit oui. Pour toi-même, annonce ton objectif à quelqu'un : tu voudras rester cohérent."),
    ("autorite", "influence", "Le biais d'autorité",
     "On fait davantage confiance aux experts et aux personnes qui ont un titre.",
     "Montre tes compétences et tes résultats sans fausse modestie. Mais devant une blouse ou un titre, vérifie quand même ce "
     "qu'on te dit."),
    ("sympathie", "influence", "La sympathie et la ressemblance",
     "On dit plus facilement oui aux gens qu'on apprécie et à ceux qui nous ressemblent.",
     "Cherche sincèrement ce que tu as en commun avec la personne en face. Et quand un vendeur te ressemble trop, garde la tête "
     "froide."),
    ("unite", "influence", "Le principe d'unité",
     "Le sentiment d'appartenir au même groupe influence fortement. « Il est des nôtres » ouvre des portes.",
     "Parle le langage de ta communauté et partage ses valeurs pour de vrai. Une appartenance jouée se sent vite."),
    ("rarete", "influence", "La rareté et l'urgence",
     "Ce qui est rare ou limité dans le temps paraît plus précieux.",
     "Devant « plus que deux en stock » ou « offre valable aujourd'hui », prends une minute avant d'acheter. Et si tu utilises "
     "la rareté, qu'elle soit vraie."),
    ("pied_porte", "influence", "Le pied dans la porte",
     "Quelqu'un qui a accepté une petite demande accepte plus facilement une demande plus grande ensuite.",
     "Commence par une petite étape facile à accepter. Et si on te demande toujours un peu plus, arrête-toi et regarde où ça "
     "mène."),
    ("porte_au_nez", "influence", "La porte au nez",
     "On fait d'abord une demande énorme, puis on recule vers ce qu'on voulait vraiment. Par contraste, la deuxième demande "
     "paraît raisonnable.",
     "Quand une proposition te semble soudain « raisonnable » après une première exagérée, juge-la seule, sans la comparer."),
    ("perte", "influence", "L'aversion à la perte",
     "Une perte fait environ deux fois plus mal qu'un gain équivalent fait plaisir. On se bat plus pour ne pas perdre que pour "
     "gagner.",
     "Pour motiver, montre ce qu'on risque de perdre en n'agissant pas. Et quand tu as peur de perdre, rappelle-toi que cette "
     "peur grossit le danger."),
    ("ancrage", "influence", "L'effet d'ancrage",
     "Le premier chiffre qu'on entend influence fortement tous les jugements qui suivent.",
     "Dans une négociation, annonce ton chiffre en premier. Et quand on t'annonce un prix barré, juge le prix final, pas la "
     "réduction."),
    ("leurre", "influence", "L'effet leurre",
     "Ajouter une troisième option moins intéressante rend l'une des deux autres beaucoup plus attirante.",
     "Quand une option semble « évidente », regarde si une autre n'a pas été placée là juste pour la faire briller."),
    ("cadrage", "influence", "L'effet de cadrage",
     "La façon de présenter les mêmes faits change la façon dont on les perçoit. « 90 % de réussite » et « 10 % d'échec » "
     "disent la même chose.",
     "Présente tes propositions sous leur angle positif. Et quand on te présente un chiffre, retourne-le pour voir l'autre "
     "face."),
    ("contraste", "influence", "L'effet de contraste",
     "Une chose paraît différente selon ce à quoi on la compare.",
     "Pour montrer un progrès, montre d'abord clairement l'avant. Et avant d'acheter, compare avec ce qui compte vraiment, pas "
     "avec ce qu'on te met à côté."),
    # --- psychologie de l'argent
    ("prix_9", "argent", "Le prix qui finit par 9",
     "Un prix qui finit par 9 paraît nettement plus bas que le chiffre rond suivant : 99 semble bien moins cher que 100. Le "
     "premier chiffre domine la perception.",
     "Arrondis toujours les prix au chiffre supérieur dans ta tête avant de décider."),
    ("prix_rond", "argent", "Le prix rond",
     "Les chiffres ronds paraissent plus haut de gamme et sont plus faciles à lire. 100 évoque la qualité, 99 la bonne affaire.",
     "Si tu vends une prestation haut de gamme, choisis un prix rond. Pour une offre économique, un prix en 9."),
    ("regle_100", "argent", "La règle des 100",
     "Sous 100, une réduction en pourcentage paraît plus grande (« 20 % »). Au-dessus de 100, une réduction en montant paraît "
     "plus grande (« 50 de moins »).",
     "Quand tu fais une promotion, choisis la forme qui paraît la plus grande. Quand tu en vois une, calcule le montant réel."),
    ("trois_offres", "argent", "Les trois offres",
     "On juge un prix par rapport aux autres options présentées. L'offre du milieu paraît raisonnable entre une offre chère "
     "et une offre basique.",
     "Si tu proposes trois formules, mets au milieu celle que tu recommandes. Si on t'en propose trois, demande-toi si tu as "
     "vraiment besoin de celle du milieu."),
    ("compte_mental", "argent", "La comptabilité mentale",
     "On traite l'argent différemment selon d'où il vient ou à quoi il est destiné, alors que c'est le même argent. « 1 par "
     "jour » paraît moins cher que « 30 par mois ».",
     "Ramène toujours un prix à la même unité, par mois ou par an, avant de comparer. Une prime ou un cadeau en argent reste "
     "de l'argent."),
    # --- passer à l'action
    ("hick", "action", "La loi de Hick",
     "Plus il y a de choix et plus ils sont complexes, plus on met de temps à décider, et plus on abandonne.",
     "Simplifie : une seule demande claire à la fois. Un seul bouton vaut mieux que trois."),
    ("fogg", "action", "Le modèle de Fogg",
     "Un comportement arrive quand trois choses sont réunies en même temps : la motivation, la capacité et un déclencheur.",
     "Si une habitude ne prend pas, cherche ce qui manque : l'envie, la facilité ou le rappel. Souvent, c'est le rappel."),
    ("east", "action", "La méthode EAST",
     "Pour qu'on adopte un comportement, il doit être facile, attirant, social et proposé au bon moment.",
     "Pour une bonne habitude : rends-la facile, agréable, fais-la avec d'autres, et place-la au bon moment de ta journée."),
    ("comb", "action", "Le modèle COM-B",
     "Pour agir, il faut trois choses : la capacité, l'occasion et la motivation.",
     "Avant de reprocher à quelqu'un de ne pas agir, vérifie s'il sait le faire, s'il en a l'occasion, et s'il en a envie."),
    ("activation", "action", "L'énergie d'activation",
     "Le plus dur, c'est de commencer. Une première étape trop lourde bloque l'action, même si le reste est facile.",
     "Rends la première étape ridiculement simple : enfiler ses chaussures, ouvrir le document, écrire une phrase."),
    ("nudge", "action", "Le coup de pouce",
     "De petits changements dans la façon de présenter un choix influencent beaucoup la décision, sans rien interdire.",
     "Arrange ton environnement pour que le bon choix soit le plus simple : les fruits en vue, le téléphone dans l'autre pièce."),
    ("cobra", "action", "L'effet cobra",
     "Une récompense mal pensée peut produire l'effet inverse de celui qu'on cherchait.",
     "Avant de créer une prime ou une règle, demande-toi comment quelqu'un pourrait la contourner à son avantage."),
    ("aida", "action", "La méthode AIDA",
     "Pour convaincre, on suit quatre étapes : attirer l'attention, susciter l'intérêt, éveiller le désir, puis appeler à "
     "l'action.",
     "Avant de demander quoi que ce soit, assure-toi d'avoir d'abord capté l'attention et l'intérêt."),
    ("sept", "action", "La règle des 7 contacts",
     "Il faut en général environ 7 contacts avant qu'une personne passe à l'action. Une seule publicité convainc rarement.",
     "Ne te décourage pas après un premier message sans réponse. La présence régulière finit par compter."),
    # --- penser mieux
    ("premiers_principes", "penser", "Les premiers principes",
     "On décompose un problème jusqu'aux vérités de base, puis on reconstruit à partir de là, au lieu de copier les autres. On "
     "peut demander « pourquoi » cinq fois de suite pour trouver la vraie cause.",
     "Devant un problème, demande « pourquoi » cinq fois avant de chercher la solution."),
    ("jtbd", "penser", "Le travail à accomplir",
     "On n'achète pas un produit, on l'« embauche » pour accomplir une tâche. Celui qui achète une perceuse veut un trou, pas "
     "une perceuse.",
     "Parle du résultat que ton client veut obtenir, pas des caractéristiques de ce que tu vends."),
    ("competence", "penser", "Le cercle de compétence",
     "Il faut savoir où l'on est vraiment bon, et y rester, ou en sortir seulement en apprenant ou en se faisant aider.",
     "Concentre ton énergie là où tu es vraiment fort, et entoure-toi pour le reste."),
    ("inversion", "penser", "L'inversion",
     "Au lieu de se demander comment réussir, on se demande ce qui garantirait l'échec, puis on l'évite.",
     "Pour ton prochain projet, fais la liste de tout ce qui le ferait échouer, et règle chaque point un par un."),
    ("ockham", "penser", "Le rasoir d'Ockham",
     "L'explication la plus simple est souvent la bonne.",
     "Quand quelque chose ne marche pas, vérifie d'abord l'évidence avant d'imaginer une cause compliquée."),
    ("pareto", "penser", "La loi de Pareto",
     "Environ 80 % des résultats viennent de 20 % des efforts.",
     "Repère les quelques actions qui produisent l'essentiel de tes résultats, et donne-leur la priorité."),
    ("goulot", "penser", "La théorie des contraintes",
     "Tout système a un point de blocage qui limite tout le reste. Améliorer ailleurs ne sert à rien tant qu'il n'est pas "
     "réglé.",
     "Trouve ce qui te freine le plus en ce moment et concentre-toi uniquement là-dessus."),
    ("cout_opportunite", "penser", "Le coût d'opportunité",
     "Chaque choix a un coût caché : ce à quoi on renonce en ne choisissant pas autre chose.",
     "Avant de dire oui, demande-toi à quoi tu dis non en même temps."),
    ("rendements", "penser", "Les rendements décroissants",
     "Au-delà d'un certain point, chaque effort supplémentaire rapporte de moins en moins.",
     "Quand tes efforts rapportent de moins en moins, change d'approche au lieu d'insister."),
    ("second_ordre", "penser", "La pensée de second ordre",
     "On regarde non seulement les effets immédiats d'une décision, mais aussi les effets de ces effets.",
     "Avant de décider, demande-toi : « et ensuite, qu'est-ce qui se passe ? » Une promotion fait vendre aujourd'hui, mais "
     "peut habituer les clients à attendre les soldes."),
    ("carte", "penser", "La carte n'est pas le territoire",
     "Nos modèles et nos chiffres décrivent la réalité, mais ne sont pas la réalité.",
     "Ne te fie pas qu'aux tableaux et aux statistiques : va parler aux vraies personnes."),
    ("probabilites", "penser", "Penser en probabilités",
     "On raisonne en chances plutôt qu'en certitudes, et on prépare plusieurs scénarios.",
     "Ne mise jamais tout sur une seule option. Prévois ce que tu feras si ton plan principal ne marche pas."),
    ("haltere", "penser", "La stratégie de l'haltère",
     "On combine une base très sûre avec quelques petits paris audacieux, en évitant le milieu tiède.",
     "Garde l'essentiel de ton énergie sur ce qui marche, et réserve une petite part à l'essai de nouvelles choses."),
    ("survivant", "penser", "Le biais du survivant",
     "On regarde seulement ceux qui ont réussi, en oubliant tous ceux qui ont échoué et qu'on ne voit pas.",
     "Avant de copier une réussite, demande-toi combien ont essayé la même chose sans réussir."),
    # --- réussir sur la durée
    ("boucles", "reussir", "Les boucles de rétroaction",
     "Le résultat d'une action devient le point de départ de la suivante. Une boucle positive accélère, une boucle négative "
     "fait décliner.",
     "Repère ce qui s'auto-entretient dans ta vie, en bien ou en mal, et nourris les bonnes boucles."),
    ("interets_composes", "reussir", "L'effet cumulé",
     "De petits progrès réguliers s'additionnent et finissent par produire de grands résultats.",
     "Commence tôt et reste régulier. Un petit effort chaque jour bat un gros effort de temps en temps."),
    ("volant", "reussir", "L'effet volant d'inertie",
     "Un effort soutenu crée un élan qui finit par se maintenir presque tout seul. Dur à lancer, facile à entretenir.",
     "Les débuts sont toujours les plus lourds : tiens bon, l'élan vient après."),
    ("changer_coute", "reussir", "Le coût du changement",
     "Changer de fournisseur, d'outil ou d'habitude coûte du temps, de l'argent et de l'effort. C'est ce qui retient les gens.",
     "Pour fidéliser, rends ton service vraiment utile au quotidien. Et pour toi, ne reste pas quelque part seulement parce "
     "que partir te fatigue."),
    ("explorer", "reussir", "Explorer ou exploiter",
     "Il faut trouver l'équilibre entre essayer de nouvelles choses et tirer le meilleur de ce qui marche déjà.",
     "N'abandonne pas ce qui fonctionne pour la dernière nouveauté, mais garde un peu de place pour l'essai."),
    ("masse_critique", "reussir", "La masse critique",
     "Il existe un seuil au-delà duquel la croissance se nourrit d'elle-même.",
     "Concentre-toi sur un seul groupe de personnes jusqu'à y être solidement installé avant de t'élargir."),
    ("reseau", "reussir", "L'effet de réseau",
     "Une chose prend de la valeur à mesure que plus de gens l'utilisent.",
     "Investis dans les communautés où tu es déjà : chaque nouveau membre augmente la valeur pour tous."),
]

PAR_ID = {s[0]: s for s in SUJETS}


def prochain(publies: list[str]) -> tuple[str, str, str, str, str]:
    """Sujet suivant : les catégories tournent dans l'ordre, et dans chacune le premier sujet pas encore traité.
    Une fois tout traité, le cycle recommence (autre angle, nouveaux exemples)."""
    tour = len(publies) // len(SUJETS)
    deja = set(publies[tour * len(SUJETS):])
    ordre = list(CATEGORIES)
    derniere = PAR_ID[publies[-1]][1] if publies and publies[-1] in PAR_ID else ordre[-1]
    for k in range(1, len(ordre) + 1):
        cat = ordre[(ordre.index(derniere) + k) % len(ordre)]
        for s in SUJETS:
            if s[1] == cat and s[0] not in deja:
                return s
    return SUJETS[0]
