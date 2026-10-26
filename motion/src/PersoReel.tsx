// Reel du compte Instagram personnel de Stéphane (27/10/2026) : sans visage filmé, ses photos et ses mots.
// Scènes : photo (diaporama lent sur une de ses photos), citation (phrase en italique), texte (idée clé),
// question (fin, invite au commentaire), signature (nom + compte). Sous-titres calés sur la voix.
// Zones (1080×1920) : en-tête 60–200, contenu 240–1180, sous-titres 1230–1450, bas libre (interface Instagram).
import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";
import { loadFont as loadLora } from "@remotion/google-fonts/Lora";

const { fontFamily } = loadFont("normal", { weights: ["600", "700", "800", "900"], subsets: ["latin", "latin-ext"] });
const { fontFamily: serif } = loadLora("italic", { weights: ["500", "700"], subsets: ["latin", "latin-ext"] });

export const FPS = 30;
const NUIT = "#10131C";
const CREME = "#F6F1E7";
const OR = "#E8B04B";
const GRIS = "#A7A9B4";
const VOIX_DEBUT = 6, VOIX_FIN = 9, FONDU = 8; // images

export type ScenePerso = {
  type: "photo" | "citation" | "texte" | "liste" | "question" | "signature";
  photo?: string; // chemin relatif à public/
  ecran?: string; // phrase affichée en grand (photo, texte) ou citation
  soustitre?: string; // texte dit par la voix
  voix?: { src: string; duree: number };
  duree?: number; // secondes, sans voix
};

export type ScriptPerso = {
  rubrique: string;
  titre: string;
  nom: string; // « Stéphane Nzesseu »
  compte: string; // « @stephane_nzesseu »
  scenes: ScenePerso[];
  musique?: string;
  volume_musique?: number;
};

const longueur = (sc: ScenePerso) => sc.voix ? VOIX_DEBUT + Math.ceil(sc.voix.duree * FPS) + VOIX_FIN : Math.round((sc.duree ?? 3) * FPS);

function plan(s: ScriptPerso) {
  let t = 0;
  const scenes = s.scenes.map((sc, i) => { const p = { sc, i, debut: t, longueur: longueur(sc) }; t += p.longueur; return p; });
  return { scenes, total: t };
}
export const dureeTotalePerso = (s: ScriptPerso) => plan(s).total;

const fr = (t: string) => t.replace(/ ([?!:;»])/g, " $1").replace(/« /g, "« ");

const Entree: React.FC<{ delai?: number; children: React.ReactNode }> = ({ delai = 0, children }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: f - delai, fps, config: { damping: 20, stiffness: 120, mass: 0.8 } });
  return <div style={{ transform: `translateY(${(1 - p) * 30}px)`, opacity: p }}>{children}</div>;
};

const Entete: React.FC<{ s: ScriptPerso }> = ({ s }) => (
  <div style={{ position: "absolute", top: 70, left: 60, right: 60, display: "flex", alignItems: "center", gap: 20 }}>
    <div style={{ border: `3px solid ${OR}`, color: OR, fontFamily, fontWeight: 800, fontSize: 26, letterSpacing: 3, padding: "8px 18px", borderRadius: 40 }}>
      {s.rubrique.toUpperCase()}
    </div>
    <div style={{ flex: 1 }} />
    <div style={{ color: CREME, fontFamily, fontWeight: 700, fontSize: 28, letterSpacing: 4 }}>{s.nom.toUpperCase()}</div>
  </div>
);

// photo de Stéphane : plein cadre dans la zone de contenu, zoom lent, dégradé en bas pour la phrase
const Photo: React.FC<{ sc: ScenePerso; i: number; long: number }> = ({ sc, i, long }) => {
  const f = useCurrentFrame();
  const zoom = interpolate(f, [0, long], i % 2 ? [1.12, 1.02] : [1.02, 1.12]);
  const glisse = interpolate(f, [0, long], i % 3 === 1 ? [-20, 20] : [20, -20]);
  return (
    <div style={{ position: "absolute", top: 230, left: 50, right: 50, height: 960, borderRadius: 28, overflow: "hidden" }}>
      <Img src={staticFile(sc.photo!)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "50% 30%",
        transform: `scale(${zoom}) translateX(${glisse}px)` }} />
      <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, rgba(16,19,28,0) 45%, rgba(16,19,28,0.92) 100%)" }} />
      {sc.ecran && <div style={{ position: "absolute", left: 50, right: 50, bottom: 50 }}>
        <Entree delai={6}><div style={{ fontFamily, fontWeight: 900, fontSize: sc.ecran.length > 30 ? 60 : 72, lineHeight: 1.1, color: CREME }}>{fr(sc.ecran)}</div></Entree>
        <Entree delai={10}><div style={{ height: 8, width: 160, background: OR, borderRadius: 4, marginTop: 24 }} /></Entree>
      </div>}
    </div>
  );
};

const Citation: React.FC<{ sc: ScenePerso }> = ({ sc }) => {
  const f = useCurrentFrame();
  const mots = fr(sc.ecran ?? "").split(" ");
  const taille = (sc.ecran ?? "").length > 90 ? 64 : (sc.ecran ?? "").length > 50 ? 76 : 92;
  return (
    <div style={{ position: "absolute", top: 300, left: 90, right: 90 }}>
      <Entree><div style={{ fontFamily: serif, fontSize: 260, color: OR, lineHeight: 0.8, height: 170 }}>“</div></Entree>
      <div style={{ fontFamily: serif, fontStyle: "italic", fontWeight: 500, fontSize: taille, lineHeight: 1.22, color: CREME }}>
        {mots.map((m, k) => (
          <span key={k} style={{ opacity: interpolate(f, [8 + k * 3, 14 + k * 3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>{m} </span>
        ))}
      </div>
    </div>
  );
};

const Texte: React.FC<{ sc: ScenePerso }> = ({ sc }) => (
  <AbsoluteFill style={{ top: 230, height: 960, justifyContent: "center", padding: "0 80px" }}>
    <Entree><div style={{ height: 10, width: 120, background: OR, borderRadius: 5, marginBottom: 40 }} /></Entree>
    <Entree delai={4}><div style={{ fontFamily, fontWeight: 900, fontSize: (sc.ecran ?? "").length > 34 ? 78 : 96, lineHeight: 1.08, color: CREME }}>
      {fr(sc.ecran ?? "")}</div></Entree>
  </AbsoluteFill>
);

// « Titre : étape 1 | étape 2 | étape 3 » : les étapes arrivent une à une, numérotées
const Liste: React.FC<{ sc: ScenePerso; long: number }> = ({ sc, long }) => {
  const [titre, reste] = (sc.ecran ?? "").includes(":") ? [(sc.ecran ?? "").split(":")[0], (sc.ecran ?? "").split(":").slice(1).join(":")] : ["", sc.ecran ?? ""];
  const etapes = reste.split("|").map((x) => x.trim().replace(/^\d+\s*[.)-]\s*/, "")).filter(Boolean); // la pastille numérote déjà
  const pas = Math.max(8, Math.floor((long - 20) / Math.max(1, etapes.length)));
  return (
    <div style={{ position: "absolute", top: 300, left: 80, right: 80 }}>
      {titre && <Entree><div style={{ fontFamily, fontWeight: 900, fontSize: 64, color: OR, marginBottom: 50 }}>{fr(titre.trim())}</div></Entree>}
      {etapes.map((e, k) => (
        <Entree key={k} delai={6 + k * pas}>
          <div style={{ display: "flex", alignItems: "center", gap: 30, marginBottom: 44 }}>
            <div style={{ minWidth: 90, height: 90, borderRadius: 45, background: OR, color: NUIT, fontFamily, fontWeight: 900, fontSize: 52,
              display: "flex", alignItems: "center", justifyContent: "center" }}>{k + 1}</div>
            <div style={{ fontFamily, fontWeight: 800, fontSize: e.length > 28 ? 52 : 60, lineHeight: 1.12, color: CREME }}>{fr(e)}</div>
          </div>
        </Entree>
      ))}
    </div>
  );
};

const Question: React.FC<{ sc: ScenePerso }> = ({ sc }) => (
  <div style={{ position: "absolute", top: 340, left: 80, right: 80 }}>
    <Entree><div style={{ fontFamily: serif, fontSize: 200, color: OR, lineHeight: 1 }}>?</div></Entree>
    <Entree delai={4}><div style={{ fontFamily, fontWeight: 900, fontSize: 70, color: CREME, lineHeight: 1.12, marginTop: 20 }}>{fr(sc.ecran ?? "")}</div></Entree>
    <Entree delai={10}><div style={{ display: "inline-block", marginTop: 50, border: `3px solid ${OR}`, color: OR, fontFamily, fontWeight: 800,
      fontSize: 40, padding: "14px 28px", borderRadius: 40 }}>Dis-le moi en commentaire</div></Entree>
  </div>
);

const Signature: React.FC<{ s: ScriptPerso }> = ({ s }) => (
  <AbsoluteFill style={{ top: 230, height: 960, alignItems: "center", justifyContent: "center", textAlign: "center" }}>
    <Entree><div style={{ fontFamily: serif, fontStyle: "italic", fontWeight: 700, fontSize: 110, color: CREME }}>{s.nom}</div></Entree>
    <Entree delai={5}><div style={{ height: 6, width: 200, background: OR, borderRadius: 3, margin: "30px auto" }} /></Entree>
    <Entree delai={8}><div style={{ fontFamily, fontWeight: 700, fontSize: 44, color: OR, letterSpacing: 2 }}>{s.compte}</div></Entree>
  </AbsoluteFill>
);

function blocs(texte: string): string[][] {
  const mots = texte.split(/ +/).filter(Boolean);
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

const SousTitres: React.FC<{ sc: ScenePerso }> = ({ sc }) => {
  const f = useCurrentFrame();
  if (!sc.voix || !sc.soustitre || sc.type === "citation") return null; // la citation est déjà le texte dit
  const b = blocs(fr(sc.soustitre));
  const total = b.reduce((n, x) => n + x.join(" ").length, 0);
  const images = sc.voix.duree * FPS;
  let t = VOIX_DEBUT, actif = b.length - 1;
  for (let k = 0; k < b.length; k++) { t += images * b[k].join(" ").length / total; if (f < t) { actif = k; break; } }
  if (f < VOIX_DEBUT) return null;
  return (
    <div style={{ position: "absolute", top: 1240, left: 60, right: 60, height: 210, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ background: "rgba(246,241,231,0.95)", borderRadius: 14, padding: "14px 26px", textAlign: "center", fontFamily, fontWeight: 800,
        fontSize: 50, lineHeight: 1.18, color: NUIT }}>{b[actif].join(" ")}</div>
    </div>
  );
};

export const PersoReel: React.FC<ScriptPerso> = (s) => {
  const { scenes, total } = plan(s);
  const f = useCurrentFrame();
  const parole = scenes.filter((p) => p.sc.voix).map((p) => [p.debut + VOIX_DEBUT, p.debut + VOIX_DEBUT + Math.ceil(p.sc.voix!.duree * FPS)]);
  const attenuation = (x: number) => Math.min(1, ...parole.map(([a, b]) =>
    interpolate(x, [a - 8, a, b, b + 8], [1, 0.3, 0.3, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })));
  return (
    <AbsoluteFill style={{ backgroundColor: NUIT, fontFamily }}>
      {scenes.map((p) => (
        <Sequence key={p.i} from={p.debut} durationInFrames={p.longueur}>
          <AbsoluteFill style={{ opacity: interpolate(f - p.debut, [0, FONDU, p.longueur - FONDU, p.longueur], [0, 1, 1, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
            {p.sc.type === "photo" && (p.sc.photo ? <Photo sc={p.sc} i={p.i} long={p.longueur} /> : <Texte sc={p.sc} />)}
            {p.sc.type === "citation" && <Citation sc={p.sc} />}
            {p.sc.type === "texte" && <Texte sc={p.sc} />}
            {p.sc.type === "liste" && <Liste sc={p.sc} long={p.longueur} />}
            {p.sc.type === "question" && <Question sc={p.sc} />}
            {p.sc.type === "signature" && <Signature s={s} />}
          </AbsoluteFill>
          <SousTitres sc={p.sc} />
          {p.sc.voix && <Sequence from={VOIX_DEBUT}><Audio src={staticFile(p.sc.voix.src)} /></Sequence>}
        </Sequence>
      ))}
      <Entete s={s} />
      <div style={{ position: "absolute", top: 0, left: 0, height: 8, width: `${(f / total) * 100}%`, background: OR }} />
      {s.musique && (
        <Audio src={staticFile(s.musique)} loop
          volume={(x) => (s.volume_musique ?? 0.10) * attenuation(x) * interpolate(x, [0, 15, total - 30, total], [0, 1, 1, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      )}
    </AbsoluteFill>
  );
};
