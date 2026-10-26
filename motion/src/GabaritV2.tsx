// Gabarit V2 (prototype, 26/10/2026) : en-tête fixe + titre collant, une phrase courte par scène,
// sous-titres calés sur la voix, source dans chaque scène, volet orange entre les scènes, fin en question.
// Zones (1080×1920) : en-tête 60–300, contenu 320–1150, source ~1165, sous-titres 1230–1450, bas libre.
import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";
import { Dessin, type Illustration } from "./Illustrations";

const { fontFamily } = loadFont("normal", { weights: ["600", "700", "800", "900"], subsets: ["latin", "latin-ext"] });

export const FPS = 30;
const NOIR = "#0E0E0E";
const BLANC = "#FFFFFF";
const ORANGE = "#F26A1B";
const GRIS = "#9A9AA2";
const VOIX_DEBUT = 5, VOIX_FIN = 7, VOLET = 4; // images

export type SceneV2 = {
  type: "visuel" | "texte" | "explication" | "question" | "outro";
  illustration?: Illustration; // scène « explication » : dessin animé + phrase courte (`ecran`)
  ecran?: string;
  etiquette?: string; // « LE FAIT », « EXEMPLE CONCRET », « CE QU'IL FAUT FAIRE »
  cas?: string; // « CONTRAT A » : de quel cas parle le montant affiché
  icone?: string;
  chiffre?: string; // « 10,99 % » : affiché en grand si présent, sinon le visuel recadré
  texte?: string; // question finale
  soustitre?: string; // texte dit par la voix, tel qu'écrit
  voix?: { src: string; duree: number };
  duree?: number; // secondes, sans voix
};

export type ScriptV2 = {
  rubrique: string;
  lieu?: string;
  date?: string;
  titre: string;
  image: string;
  source?: string;
  scenes: SceneV2[];
  musique?: string;
  volume_musique?: number;
};

const longueur = (sc: SceneV2) => sc.voix ? VOIX_DEBUT + Math.ceil(sc.voix.duree * FPS) + VOIX_FIN : Math.round((sc.duree ?? 3) * FPS);

function plan(s: ScriptV2) {
  let t = 0;
  const scenes = s.scenes.map((sc, i) => { const p = { sc, i, debut: t, longueur: longueur(sc) }; t += p.longueur; return p; });
  return { scenes, total: t };
}
export const dureeTotaleV2 = (s: ScriptV2) => plan(s).total;

// typographie française : jamais de retour à la ligne avant « ? », « ! », « : », « ; »
const fr = (t: string) => t.replace(/ ([?!:;])/g, " $1");

// mots en orange : chiffres, pourcentages, sigles (CEMAC, BEAC)
const estCle = (mot: string) => /\d|%|^[A-ZÉÈ]{3,}[.,;:!?]?$/.test(mot);

const Entree: React.FC<{ delai?: number; children: React.ReactNode }> = ({ delai = 0, children }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: f - delai, fps, config: { damping: 18, stiffness: 150, mass: 0.7 } });
  return <div style={{ transform: `translateY(${(1 - p) * 40}px)`, opacity: p }}>{children}</div>;
};

const Entete: React.FC<{ s: ScriptV2 }> = ({ s }) => {
  const mots = fr(s.titre).split(" ");
  const taille = s.titre.length > 80 ? 42 : s.titre.length > 50 ? 50 : 58;
  return (
    <div style={{ position: "absolute", top: 60, left: 60, right: 60 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        <div style={{ background: ORANGE, color: BLANC, fontFamily, fontWeight: 800, fontSize: 28, letterSpacing: 2, padding: "8px 18px", borderRadius: 6 }}>{s.rubrique}</div>
        <div style={{ flex: 1, color: GRIS, fontFamily, fontWeight: 700, fontSize: 28, letterSpacing: 1 }}>{[s.lieu, s.date].filter(Boolean).join(" · ").toUpperCase()}</div>
        {/* monogramme < 100 px */}
        <div style={{ width: 72, height: 72, borderRadius: 12, background: BLANC, display: "flex", alignItems: "center", justifyContent: "center",
          fontFamily, fontWeight: 900, fontSize: 50, color: NOIR }}>D<span style={{ color: ORANGE }}>.</span></div>
      </div>
      <div style={{ marginTop: 22, fontFamily, fontWeight: 900, fontSize: taille, lineHeight: 1.12, color: BLANC }}>
        {mots.map((m, k) => <span key={k} style={{ color: estCle(m) ? ORANGE : BLANC }}>{m} </span>)}
      </div>
    </div>
  );
};

// visuel du lot recadré : chaque scène zoome sur une zone différente de la photo. Le visuel est une affiche
// (photo en haut, texte incrusté en bas) : les recadrages restent dans le haut pour ne jamais couper le texte.
const Visuel: React.FC<{ s: ScriptV2; i: number; long: number; etiquette?: string }> = ({ s, i, long, etiquette }) => {
  const f = useCurrentFrame();
  const foyers = [[50, 8], [35, 8], [80, 0], [60, 10]]; // le coin haut gauche porte le logo du visuel : évité
  const [x, y] = i === 0 ? [50, 50] : foyers[i % foyers.length];
  const zoom = interpolate(f, [0, long], i === 0 ? [1.0, 1.06] : [1.85, 1.95]);
  return (
    <div style={{ position: "absolute", top: 330, left: 140, width: 800, height: 800, borderRadius: 24, overflow: "hidden", border: `6px solid ${ORANGE}` }}>
      <Img src={staticFile(s.image)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})`, transformOrigin: `${x}% ${y}%` }} />
      <div style={{ position: "absolute", left: 20, bottom: 20, background: "rgba(14,14,14,0.85)", color: BLANC, fontFamily, fontWeight: 700,
        fontSize: 22, letterSpacing: 2, padding: "6px 14px", borderRadius: 4 }}>ILLUSTRATION</div>
      {etiquette && <div style={{ position: "absolute", left: 20, top: 20 }}><Entree><div style={{ background: ORANGE, color: BLANC, fontFamily,
        fontWeight: 900, fontSize: 40, letterSpacing: 2, padding: "10px 22px", borderRadius: 6 }}>{etiquette}</div></Entree></div>}
    </div>
  );
};

const Chiffre: React.FC<{ sc: SceneV2 }> = ({ sc }) => (
  <AbsoluteFill style={{ top: 330, height: 820, alignItems: "center", justifyContent: "center" }}>
    <Entree><div style={{ display: "flex", alignItems: "center", gap: 18, justifyContent: "center" }}>
      {sc.icone && <div style={{ fontSize: 70 }}>{sc.icone}</div>}
      <div style={{ fontFamily, fontWeight: 900, fontSize: 44, letterSpacing: 3, color: ORANGE }}>{sc.etiquette}</div>
    </div></Entree>
    {sc.cas && <Entree delai={3}><div style={{ marginTop: 30, border: `4px solid ${BLANC}`, color: BLANC, fontFamily, fontWeight: 900,
      fontSize: 56, letterSpacing: 3, padding: "8px 30px", borderRadius: 10 }}>{sc.cas}</div></Entree>}
    <Entree delai={5}><div style={{ fontFamily, fontWeight: 900, fontSize: sc.chiffre!.length > 12 ? 112 : sc.chiffre!.length > 9 ? 140 : 210,
      color: BLANC, lineHeight: 1.05, textAlign: "center", marginTop: 30, whiteSpace: "nowrap" }}>{sc.chiffre}</div></Entree>
    <Entree delai={9}><div style={{ height: 12, width: 260, background: ORANGE, borderRadius: 6, marginTop: 30 }} /></Entree>
  </AbsoluteFill>
);

const Explication: React.FC<{ sc: SceneV2 }> = ({ sc }) => (
  <>
    {sc.etiquette && <div style={{ position: "absolute", top: 335, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
      <Entree><div style={{ background: ORANGE, color: BLANC, fontFamily, fontWeight: 900, fontSize: 40, letterSpacing: 3,
        padding: "8px 26px", borderRadius: 6 }}>{sc.etiquette}</div></Entree></div>}
    <div style={{ position: "absolute", top: 410, left: 160 }}><Dessin il={sc.illustration!} /></div>
    {sc.ecran && <div style={{ position: "absolute", top: 945, left: 60, right: 60, textAlign: "center" }}>
      <Entree delai={8}><div style={{ fontFamily, fontWeight: 900, fontSize: sc.ecran.length > 28 ? 58 : 68, lineHeight: 1.1, color: BLANC }}>
        {fr(sc.ecran).split(" ").map((m, k) => <span key={k} style={{ color: estCle(m) ? ORANGE : BLANC }}>{m} </span>)}
      </div></Entree></div>}
  </>
);

const Question: React.FC<{ sc: SceneV2 }> = ({ sc }) => (
  <div style={{ position: "absolute", top: 380, left: 70, right: 70 }}>
    <Entree><div style={{ fontFamily, fontWeight: 900, fontSize: 180, color: ORANGE, lineHeight: 1 }}>?</div></Entree>
    <Entree delai={4}><div style={{ fontFamily, fontWeight: 900, fontSize: 72, color: BLANC, lineHeight: 1.12, marginTop: 20 }}>{fr(sc.texte ?? "")}</div></Entree>
    <Entree delai={10}><div style={{ display: "inline-block", marginTop: 50, background: ORANGE, color: BLANC, fontFamily, fontWeight: 800,
      fontSize: 44, padding: "16px 30px", borderRadius: 40 }}>Dis-le en commentaire 👇</div></Entree>
  </div>
);

const Outro: React.FC<{ s: ScriptV2 }> = ({ s }) => (
  <AbsoluteFill style={{ top: 330, height: 820, alignItems: "center", justifyContent: "center", textAlign: "center" }}>
    <Entree><div style={{ fontFamily, fontWeight: 900, fontSize: 120, color: BLANC }}>DEC<span style={{ color: ORANGE }}>I</span>DE
      <span style={{ fontWeight: 600, fontSize: 50, marginLeft: 8 }}>media</span></div></Entree>
    <Entree delai={4}><div style={{ fontFamily, fontWeight: 800, fontSize: 52, color: ORANGE, marginTop: 20 }}>Abonne-toi pour comprendre</div></Entree>
    {s.source && <Entree delai={8}><div style={{ fontFamily, fontWeight: 600, fontSize: 32, color: GRIS, marginTop: 50, padding: "0 80px" }}>{s.source}</div></Entree>}
  </AbsoluteFill>
);

// sous-titres : blocs de 5 à 8 mots, chaque bloc reste à l'écran un temps proportionnel à sa longueur
function blocs(texte: string): string[][] {
  const mots = texte.split(/ +/).filter(Boolean); // espace simple seulement : l'insécable lie un nombre à son unité
  const out: string[][] = [];
  let bloc: string[] = [];
  mots.forEach((m, k) => {
    bloc.push(m);
    const reste = mots.length - k - 1;
    if ((bloc.length >= 5 && /[,.;:!?]$/.test(m) && reste >= 3) || (bloc.length >= 7 && reste >= 3) || bloc.length >= 8) {
      out.push(bloc); bloc = [];
    }
  });
  if (bloc.length) { if (bloc.length < 3 && out.length) out[out.length - 1].push(...bloc); else out.push(bloc); }
  return out;
}

const SousTitres: React.FC<{ sc: SceneV2 }> = ({ sc }) => {
  const f = useCurrentFrame();
  if (!sc.voix || !sc.soustitre) return null;
  const b = blocs(fr(sc.soustitre));
  const total = b.reduce((n, x) => n + x.join(" ").length, 0);
  const images = sc.voix.duree * FPS;
  let t = VOIX_DEBUT, actif = b.length - 1;
  for (let k = 0; k < b.length; k++) { t += images * b[k].join(" ").length / total; if (f < t) { actif = k; break; } }
  if (f < VOIX_DEBUT) return null;
  return (
    <div style={{ position: "absolute", top: 1230, left: 60, right: 60, height: 220, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ background: "rgba(14,14,14,0.88)", borderRadius: 14, padding: "14px 26px", textAlign: "center", fontFamily, fontWeight: 800,
        fontSize: 54, lineHeight: 1.18, color: BLANC }}>
        {b[actif].map((m, k) => <span key={k} style={{ color: estCle(m) ? ORANGE : BLANC }}>{m} </span>)}
      </div>
    </div>
  );
};

export const GabaritV2: React.FC<ScriptV2> = (s) => {
  const { scenes, total } = plan(s);
  const f = useCurrentFrame();
  const parole = scenes.filter((p) => p.sc.voix).map((p) => [p.debut + VOIX_DEBUT, p.debut + VOIX_DEBUT + Math.ceil(p.sc.voix!.duree * FPS)]);
  const attenuation = (fr: number) => Math.min(1, ...parole.map(([a, b]) =>
    interpolate(fr, [a - 8, a, b, b + 8], [1, 0.35, 0.35, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })));
  return (
    <AbsoluteFill style={{ backgroundColor: NOIR, fontFamily }}>
      {scenes.map((p) => (
        <Sequence key={p.i} from={p.debut} durationInFrames={p.longueur}>
          {p.sc.type === "visuel" && <Visuel s={s} i={0} long={p.longueur} />}
          {p.sc.type === "texte" && (p.sc.chiffre ? <Chiffre sc={p.sc} /> : <Visuel s={s} i={p.i} long={p.longueur} etiquette={p.sc.etiquette} />)}
          {p.sc.type === "explication" && <Explication sc={p.sc} />}
          {p.sc.type === "question" && <Question sc={p.sc} />}
          {p.sc.type === "outro" && <Outro s={s} />}
          {s.source && p.sc.type !== "outro" && (
            <div style={{ position: "absolute", top: 1160, left: 60, right: 60, fontFamily, fontWeight: 600, fontSize: 26, color: GRIS }}>{s.source}</div>
          )}
          <SousTitres sc={p.sc} />
          {p.sc.voix && <Sequence from={VOIX_DEBUT}><Audio src={staticFile(p.sc.voix.src)} /></Sequence>}
        </Sequence>
      ))}
      <Entete s={s} />
      {/* volet orange de 0,25 s à chaque changement de scène, sur la zone de contenu */}
      {scenes.slice(1).map((p) => {
        const x = interpolate(f, [p.debut - VOLET, p.debut + VOLET], [-1080, 1080], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        return f >= p.debut - VOLET && f <= p.debut + VOLET
          ? <div key={p.i} style={{ position: "absolute", top: 320, height: 1140, left: 0, width: 1080, background: ORANGE, transform: `translateX(${x}px)` }} />
          : null;
      })}
      <div style={{ position: "absolute", top: 0, left: 0, height: 10, width: `${(f / total) * 100}%`, background: ORANGE }} />
      {s.musique && (
        <Audio src={staticFile(s.musique)} loop
          volume={(fr) => (s.volume_musique ?? 0.10) * attenuation(fr) * interpolate(fr, [0, 15, total - 30, total], [0, 1, 1, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      )}
    </AbsoluteFill>
  );
};
