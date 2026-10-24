// Script d'un Short DECIDE MEDIA : produit automatiquement à partir d'un article du lot.
export type Etape = { titre: string; detail: string; icone: string };

export type Script = {
  rubrique: string; // « GUIDE PRATIQUE », « ACTUALITÉ », « DÉCRYPTAGE »
  pays?: string; // ex. « CAMEROUN »
  date?: string; // ex. « 14 octobre 2026 »
  titre: string[]; // 1 à 3 lignes courtes
  image: string; // visuel du lot (dans public/)
  accroche: string; // la phrase qui donne envie de rester
  contexte?: string; // « pour vous » : à qui ça sert, quelle décision ça éclaire
  etapes: Etape[]; // 2 à 4 idées clés
  chiffre?: { valeur: number; unite: string; legende: string; compte_a_rebours?: boolean; decimales?: number };
  liste?: { titre: string; items: string[] };
  conclusion: string;
  source?: string;
  hashtags?: string[];
  audio?: string; // voix off d'un seul tenant (dans public/)
  // voix off scène par scène : cle = titre, visuel, contexte, etape0…etape3, conclusion, outro ; duree en secondes.
  // Chaque scène dure au moins le temps de sa phrase.
  voix?: { cle: string; src: string; duree: number }[];
  musique?: string; // fond sonore (dans public/), en boucle, fondus d'entrée et de sortie
  volume_musique?: number; // 0 à 1 (défaut 0.10)
  durees?: Partial<Record<"intro" | "titre" | "visuel" | "contexte" | "etape" | "chiffre" | "liste" | "conclusion" | "outro", number>>;
};
