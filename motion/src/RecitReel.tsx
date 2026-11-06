// « Histoires vraies d'argent » (TikTok + YouTube, essais du 06/11/2026, agent/histoires.py).
// Habillage « archives » : documents d'époque en plein écran avec zoom lent (Ken Burns), grain et vignette, date
// tamponnée, chiffre géant, sous-titres karaoké. L'accroche est entière dès la PREMIÈRE image : TikTok en fait la
// couverture (correctif des Shorts DECIDE du 05/11).
// Zones sûres TikTok (1080×1920) : rien d'important au-dessus de 230, sous 1400, ni dans les 150 px de droite.
import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";
import { loadFont as loadPlayfair } from "@remotion/google-fonts/PlayfairDisplay";
import { loadFont as loadElite } from "@remotion/google-fonts/SpecialElite";
import { loadFont as loadAnton } from "@remotion/google-fonts/Anton";

const { fontFamily } = loadFont("normal", { weights: ["600", "700", "800", "900"], subsets: ["latin", "latin-ext"] });
const { fontFamily: playfair } = loadPlayfair("normal", { weights: ["700", "900"], subsets: ["latin", "latin-ext"] });
const { fontFamily: elite } = loadElite("normal", { weights: ["400"], subsets: ["latin", "latin-ext"] });
const { fontFamily: anton } = loadAnton("normal", { weights: ["400"], subsets: ["latin", "latin-ext"] });

export const FPS = 30;
const NOIR = "#120E0B";
const PAPIER = "#F3E9D2";
const OR = "#E2B04A";
const ROUGE = "#C2412D";
const VOIX_DEBUT = 3, VOIX_FIN = 5;
const G = 70, D = 150;

export type SceneRecit = {
  type: "accroche" | "recit" | "date" | "chiffre" | "suite" | "lecon" | "question" | "signature";
  ecran?: string; // *mot clé* en or
  grand?: string; // date ou chiffre en très grand
  image?: { src: string; credit: string };
  soustitre?: string;
  voix?: { src: string; duree: number };
  duree?: number;
};

export type ScriptRecit = {
  serie: string;
  titre: string;
  compte: string;
  partie?: string | null;
  format: "serie" | "serie2" | "chiffre";
  scenes: SceneRecit[];
  musique?: string;
  volume_musique?: number;
};

const longueur = (sc: SceneRecit) => sc.voix ? VOIX_DEBUT + Math.ceil(sc.voix.duree * FPS) + VOIX_FIN : Math.round((sc.duree ?? 3) * FPS);

function plan(s: ScriptRecit) {
  let t = 0;
  const scenes = s.scenes.map((sc, i) => { const p = { sc, i, debut: t, longueur: longueur(sc) }; t += p.longueur; return p; });
  return { scenes, total: t };
}
export const dureeTotaleRecit = (s: ScriptRecit) => plan(s).total;

const fr = (t: string) => t.replace(/ ([?!:;»])/g, " $1").replace(/« /g, "« ");

function motsCles(t: string): [string, boolean][] {
  const out: [string, boolean][] = [];
  let cle = false;
  for (const m of fr(t).split(" ").filter(Boolean)) {
    const debut = m.startsWith("*"), fin = m.replace(/[.,!?:;»]+$/, "").endsWith("*");
    out.push([m.replace(/\*/g, ""), cle || debut]);
    if (debut && !fin) cle = true;
    if (fin) cle = false;
  }
  return out;
}

// ---------------------------------------------------------------- fond
const Grain: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(0,0,0,0.65) 100%)" }} />
      <AbsoluteFill style={{ opacity: 0.08, backgroundImage: "repeating-linear-gradient(0deg, #fff 0px, transparent 1px, transparent 3px)",
        transform: `translateY(${(f * 7) % 4}px)` }} />
    </AbsoluteFill>
  );
};

const FondPapier: React.FC = () => (
  <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 35%, #2B2117 0%, ${NOIR} 75%)` }} />
);

// image d'archive : zoom lent alterné (avant / arrière) et léger glissement, ton sépia, assombrie en bas
const Archive: React.FC<{ im: NonNullable<SceneRecit["image"]>; long: number; i: number; fige?: boolean }> = ({ im, long, i, fige }) => {
  const f = useCurrentFrame();
  const avant = i % 2 === 0;
  const z = fige ? 1.08 : interpolate(f, [0, long], avant ? [1.04, 1.16] : [1.16, 1.04]);
  const x = fige ? 0 : interpolate(f, [0, long], [i % 3 === 0 ? -20 : 20, i % 3 === 0 ? 20 : -20]);
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Img src={staticFile(im.src)} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover", filter: "blur(28px) brightness(0.5)", transform: "scale(1.2)" }} />
      <Img src={staticFile(im.src)} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "contain",
        transform: `scale(${z}) translateX(${x}px)`, filter: "sepia(0.35) contrast(1.08) saturate(0.85)" }} />
      {/* bande sombre sous les textes (y 480–1000, titres et chiffres) : lisibilité sur gravures et photos chargées */}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(18,14,11,0.55) 0%, rgba(18,14,11,0.2) 18%, rgba(18,14,11,0.66) 25%, rgba(18,14,11,0.66) 52%, rgba(18,14,11,0.4) 57%, rgba(18,14,11,0.9) 80%)" }} />
    </AbsoluteFill>
  );
};

const Credit: React.FC<{ t?: string }> = ({ t }) => t ? (
  <div style={{ position: "absolute", top: 1385, left: G, right: D, fontFamily, fontWeight: 600, fontSize: 20, color: PAPIER, opacity: 0.7 }}>{t}</div>
) : null;

// ---------------------------------------------------------------- textes
const Mots: React.FC<{ texte: string; taille: number; police?: string; poids?: number; anime?: boolean; pas?: number }> =
  ({ texte, taille, police = fontFamily, poids = 900, anime = true, pas = 3 }) => {
    const f = useCurrentFrame();
    const { fps } = useVideoConfig();
    return (
      <span style={{ fontFamily: police, fontWeight: poids, fontSize: taille, lineHeight: 1.12, color: PAPIER, textShadow: "0 6px 24px rgba(0,0,0,0.7)" }}>
        {motsCles(texte).map(([m, cle], k) => {
          const p = anime ? spring({ frame: f - 2 - k * pas, fps, config: { damping: 12, stiffness: 200, mass: 0.5 } }) : 1;
          return (
            <span key={k} style={{ display: "inline-block", marginRight: taille * 0.25, transform: `translateY(${(1 - p) * 40}px)`, opacity: p,
              color: cle ? NOIR : PAPIER, background: cle ? OR : "transparent", padding: cle ? "0 12px" : 0, borderRadius: 8 }}>{m}</span>
          );
        })}
      </span>
    );
  };

const Bloc: React.FC<{ top: number; children: React.ReactNode }> = ({ top, children }) => (
  <div style={{ position: "absolute", top, left: G, right: D, textAlign: "center" }}>{children}</div>
);

// accroche : entière dès l'image 0 (couverture TikTok), puis respiration lente
const Accroche: React.FC<{ sc: SceneRecit }> = ({ sc }) => {
  const f = useCurrentFrame();
  const t = sc.ecran ?? "";
  return (
    <Bloc top={560}>
      <div style={{ transform: `scale(${1 + f / 1500})` }}>
        <Mots texte={t} taille={t.length > 55 ? 82 : t.length > 35 ? 96 : 112} police={playfair} anime={false} />
      </div>
    </Bloc>
  );
};

const Tampon: React.FC<{ texte: string; couleur: string; police: string; taille: number; rot?: number }> = ({ texte, couleur, police, taille, rot = -5 }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: f - 2, fps, config: { damping: 9, stiffness: 220, mass: 0.7 } });
  return (
    <div style={{ display: "inline-block", transform: `rotate(${rot}deg) scale(${2.2 - 1.2 * p})`, opacity: Math.min(1, p * 1.6),
      fontFamily: police, fontSize: taille, lineHeight: 1, color: couleur, padding: "10px 34px", border: `8px solid ${couleur}`,
      borderRadius: 14, textShadow: "0 8px 30px rgba(0,0,0,0.6)", background: "rgba(18,14,11,0.45)" }}>{texte}</div>
  );
};

const DateSc: React.FC<{ sc: SceneRecit }> = ({ sc }) => (
  <>
    <Bloc top={520}><Tampon texte={sc.grand ?? ""} couleur={OR} police={elite} taille={(sc.grand ?? "").length > 8 ? 110 : 180} /></Bloc>
    {sc.ecran && <Bloc top={820}><Mots texte={sc.ecran} taille={64} /></Bloc>}
  </>
);

const ChiffreSc: React.FC<{ sc: SceneRecit }> = ({ sc }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: f - 2, fps, config: { damping: 10, stiffness: 160 } });
  const g = sc.grand ?? "";
  return (
    <>
      <Bloc top={480}>
        <div style={{ fontFamily: anton, fontSize: g.length > 12 ? 140 : g.length > 7 ? 190 : 250, lineHeight: 1, color: OR,
          transform: `scale(${0.5 + 0.5 * p})`, opacity: p, textShadow: "0 0 60px rgba(226,176,74,0.45), 0 10px 30px rgba(0,0,0,0.7)" }}>{g}</div>
      </Bloc>
      {sc.ecran && <Bloc top={800}><Mots texte={sc.ecran} taille={62} /></Bloc>}
    </>
  );
};

const Suite: React.FC<{ sc: SceneRecit }> = ({ sc }) => (
  <>
    <Bloc top={420}><Tampon texte="À SUIVRE" couleur={ROUGE} police={elite} taille={120} rot={-7} /></Bloc>
    <Bloc top={700}><Mots texte={sc.ecran ?? ""} taille={76} police={playfair} /></Bloc>
    <Bloc top={1010}><span style={{ fontFamily, fontWeight: 900, fontSize: 48, color: NOIR, background: OR, padding: "16px 34px", borderRadius: 50 }}>Partie 2 → abonne-toi</span></Bloc>
  </>
);

const Lecon: React.FC<{ sc: SceneRecit }> = ({ sc }) => (
  <>
    <Bloc top={430}><span style={{ fontFamily: elite, fontSize: 56, color: OR, letterSpacing: 6 }}>LA LEÇON</span></Bloc>
    <Bloc top={560}><Mots texte={sc.ecran ?? ""} taille={(sc.ecran ?? "").length > 60 ? 68 : 80} police={playfair} pas={2} /></Bloc>
  </>
);

const Question: React.FC<{ sc: SceneRecit }> = ({ sc }) => (
  <>
    <Bloc top={560}><Mots texte={sc.ecran ?? ""} taille={(sc.ecran ?? "").length > 50 ? 70 : 84} police={playfair} /></Bloc>
    <Bloc top={1050}><span style={{ fontFamily, fontWeight: 900, fontSize: 44, color: NOIR, background: OR, padding: "16px 32px", borderRadius: 50 }}>Dis-le en commentaire 👇</span></Bloc>
  </>
);

const Signature: React.FC<{ s: ScriptRecit }> = ({ s }) => (
  <AbsoluteFill style={{ top: 380, height: 800, alignItems: "center", justifyContent: "center", textAlign: "center", paddingRight: D - G }}>
    <Tampon texte="VRAI" couleur={OR} police={elite} taille={120} />
    <div style={{ fontFamily: playfair, fontWeight: 900, fontSize: 84, color: PAPIER, marginTop: 50, lineHeight: 1.1 }}>{s.serie}</div>
    <div style={{ fontFamily, fontWeight: 800, fontSize: 44, color: OR, marginTop: 30 }}>
      {s.format === "serie" ? "La partie 2 arrive : abonne-toi" : "Une histoire vraie chaque jour"}
    </div>
    <div style={{ fontFamily, fontWeight: 700, fontSize: 36, color: PAPIER, marginTop: 16, opacity: 0.85 }}>{s.compte}</div>
  </AbsoluteFill>
);

const SousTitres: React.FC<{ sc: SceneRecit }> = ({ sc }) => {
  const f = useCurrentFrame();
  if (!sc.voix || !sc.soustitre || ["accroche", "lecon", "question", "signature", "suite"].includes(sc.type)) return null;
  const mots = fr(sc.soustitre).split(/ +/).filter(Boolean).reduce<string[]>((l, m) => {
    if (/^[?!:;»]+$/.test(m) && l.length) l[l.length - 1] += " " + m; else l.push(m);
    return l;
  }, []);
  const total = mots.reduce((n, m) => n + m.length + 1, 0);
  const images = sc.voix.duree * FPS;
  let t = VOIX_DEBUT, actuel = mots.length - 1;
  for (let k = 0; k < mots.length; k++) { t += images * (mots[k].length + 1) / total; if (f < t) { actuel = k; break; } }
  if (f < VOIX_DEBUT) return null;
  const debut = Math.floor(actuel / 4) * 4;
  return (
    <div style={{ position: "absolute", top: 1150, left: G, right: D, display: "flex", justifyContent: "center", flexWrap: "wrap",
      gap: "6px 22px", fontFamily, fontWeight: 900, fontSize: 58, lineHeight: 1.15, textAlign: "center",
      textShadow: "0 4px 0 #000, 0 0 18px rgba(0,0,0,0.85)", background: "rgba(18,14,11,0.62)", borderRadius: 22, padding: "14px 20px" }}>
      {mots.slice(debut, debut + 4).map((m, k) => (
        <span key={k} style={{ color: debut + k === actuel ? OR : PAPIER, transform: `scale(${debut + k === actuel ? 1.1 : 1})`, display: "inline-block" }}>{m}</span>
      ))}
    </div>
  );
};

const Entete: React.FC<{ s: ScriptRecit }> = ({ s }) => (
  <div style={{ position: "absolute", top: 240, left: G, right: D, display: "flex", justifyContent: "center", gap: 14 }}>
    <div style={{ background: "rgba(18,14,11,0.7)", border: `2px solid ${OR}`, color: OR, fontFamily: elite, fontSize: 30,
      letterSpacing: 2, padding: "6px 18px", borderRadius: 6 }}>{s.serie.toUpperCase()}</div>
    {s.partie && <div style={{ background: ROUGE, color: PAPIER, fontFamily, fontWeight: 900, fontSize: 28, padding: "8px 16px", borderRadius: 6 }}>{s.partie.toUpperCase()}</div>}
  </div>
);

const Entree: React.FC<{ children: React.ReactNode; long: number; immediate?: boolean }> = ({ children, long, immediate }) => {
  const f = useCurrentFrame();
  const entree = immediate ? 1 : interpolate(f, [0, 6], [0, 1], { extrapolateRight: "clamp" });
  const sortie = interpolate(f, [long - 4, long], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ opacity: Math.min(entree, sortie) }}>{children}</AbsoluteFill>;
};

export type CouvertureRecit = { serie: string; accroche: string; image?: { src: string; credit: string } | null; partie?: string | null; compte: string };

export const RecitCouverture: React.FC<CouvertureRecit> = (c) => (
  <AbsoluteFill style={{ backgroundColor: NOIR }}>
    <FondPapier />
    {c.image && <Archive im={c.image} long={30} i={0} fige />}
    <Entete s={{ serie: c.serie, partie: c.partie, titre: "", compte: c.compte, format: "serie", scenes: [] }} />
    <Bloc top={560}><Mots texte={c.accroche} taille={c.accroche.length > 55 ? 88 : c.accroche.length > 35 ? 104 : 120} police={playfair} anime={false} /></Bloc>
    <Grain />
  </AbsoluteFill>
);

export const RecitReel: React.FC<ScriptRecit> = (s) => {
  const { scenes, total } = plan(s);
  const f = useCurrentFrame();
  const parole = scenes.filter((p) => p.sc.voix).map((p) => [p.debut + VOIX_DEBUT, p.debut + VOIX_DEBUT + Math.ceil(p.sc.voix!.duree * FPS)]);
  const attenuation = (x: number) => Math.min(1, ...parole.map(([a, b]) =>
    interpolate(x, [a - 8, a, b, b + 8], [1, 0.35, 0.35, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })));
  return (
    <AbsoluteFill style={{ backgroundColor: NOIR }}>
      <FondPapier />
      {scenes.map((p) => (
        <Sequence key={p.i} from={p.debut} durationInFrames={p.longueur}>
          {p.sc.image && <Archive im={p.sc.image} long={p.longueur} i={p.i} />}
          <Entree long={p.longueur} immediate={p.i === 0}>
            {p.sc.type === "accroche" && <Accroche sc={p.sc} />}
            {p.sc.type === "recit" && <Bloc top={620}><Mots texte={p.sc.ecran ?? ""} taille={(p.sc.ecran ?? "").length > 34 ? 72 : 86} /></Bloc>}
            {p.sc.type === "date" && <DateSc sc={p.sc} />}
            {p.sc.type === "chiffre" && <ChiffreSc sc={p.sc} />}
            {p.sc.type === "suite" && <Suite sc={p.sc} />}
            {p.sc.type === "lecon" && <Lecon sc={p.sc} />}
            {p.sc.type === "question" && <Question sc={p.sc} />}
            {p.sc.type === "signature" && <Signature s={s} />}
          </Entree>
          <SousTitres sc={p.sc} />
          {p.sc.image && <Credit t={p.sc.image.credit} />}
          {p.sc.voix && <Sequence from={VOIX_DEBUT}><Audio src={staticFile(p.sc.voix.src)} /></Sequence>}
        </Sequence>
      ))}
      <Grain />
      <Entete s={s} />
      <div style={{ position: "absolute", top: 0, left: 0, height: 10, width: `${(f / total) * 100}%`, background: `linear-gradient(90deg, ${ROUGE}, ${OR})` }} />
      {s.musique && (
        <Audio src={staticFile(s.musique)} loop
          volume={(x) => (s.volume_musique ?? 0.1) * attenuation(x) * interpolate(x, [0, 15, total - 30, total], [0, 1, 1, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      )}
    </AbsoluteFill>
  );
};
