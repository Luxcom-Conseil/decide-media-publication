// Reel « conseils et astuces psychologiques » du compte Instagram de Stéphane (v2, 27/10/2026).
// Rythme : une scène courte par idée, entrée en « punch » (zoom + flash), émoji animé, texte cinétique mot à mot avec
// mots clés en or, sous-titres karaoké, fond animé ou vidéo/photo réaliste (Pexels) assombrie.
// Zones sûres Instagram (1080×1920) : rien d'important au-dessus de 230, en dessous de 1400, ni dans les 150 px de
// droite (boutons). En-tête 250, émoji 360–560, texte 600–1080, sous-titres 1130–1330.
import React from "react";
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";
import { loadFont as loadLora } from "@remotion/google-fonts/Lora";

const { fontFamily } = loadFont("normal", { weights: ["600", "700", "800", "900"], subsets: ["latin", "latin-ext"] });
const { fontFamily: serif } = loadLora("italic", { weights: ["500", "700"], subsets: ["latin", "latin-ext"] });

export const FPS = 30;
const NUIT = "#0F1020";
const VIOLET = "#2A1E4D";
const CREME = "#FFF8EC";
const OR = "#FFC23D";
const CORAIL = "#FF6B5A";
const VOIX_DEBUT = 3, VOIX_FIN = 5; // images : rythme serré
const G = 70, D = 150; // marges gauche / droite (boutons Instagram à droite)

export type ScenePerso = {
  type: "accroche" | "texte" | "liste" | "comparaison" | "citation" | "question" | "signature";
  emoji?: string;
  ecran?: string; // *mot clé* en or
  a?: string; b?: string; valeur_a?: number; valeur_b?: number; // comparaison
  media?: { src: string; video: boolean };
  soustitre?: string;
  voix?: { src: string; duree: number };
  duree?: number;
};

export type ScriptPerso = {
  rubrique: string;
  titre: string;
  nom: string;
  compte: string;
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

// « Tu *détestes* perdre » → [["Tu", false], ["détestes", true], ["perdre", false]]
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
const Fond: React.FC = () => {
  const f = useCurrentFrame();
  const bulle = (x: number, y: number, r: number, c: string, v: number) => (
    <div style={{ position: "absolute", left: x + Math.sin(f / v) * 120, top: y + Math.cos(f / (v * 1.3)) * 140, width: r, height: r,
      borderRadius: r, background: c, filter: "blur(120px)", opacity: 0.55 }} />
  );
  return (
    <AbsoluteFill style={{ background: `linear-gradient(160deg, ${NUIT} 0%, ${VIOLET} 100%)`, overflow: "hidden" }}>
      {bulle(-200, 200, 700, "#6C3BFF", 70)}
      {bulle(600, 1100, 650, CORAIL, 90)}
      {bulle(300, 600, 500, OR, 110)}
    </AbsoluteFill>
  );
};

const Media: React.FC<{ m: NonNullable<ScenePerso["media"]>; long: number }> = ({ m, long }) => {
  const f = useCurrentFrame();
  const zoom = interpolate(f, [0, long], [1.05, 1.18]);
  const style: React.CSSProperties = { width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})` };
  return (
    <AbsoluteFill>
      {m.video ? <OffthreadVideo src={staticFile(m.src)} muted style={style} /> : <Img src={staticFile(m.src)} style={style} />}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(15,16,32,0.55) 0%, rgba(15,16,32,0.35) 35%, rgba(15,16,32,0.85) 75%)" }} />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- éléments
const Pop: React.FC<{ delai?: number; children: React.ReactNode; style?: React.CSSProperties }> = ({ delai = 0, children, style }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: f - delai, fps, config: { damping: 11, stiffness: 180, mass: 0.6 } });
  return <div style={{ transform: `scale(${0.4 + 0.6 * p})`, opacity: Math.min(1, p * 1.5), ...style }}>{children}</div>;
};

const Emoji: React.FC<{ e?: string; taille?: number }> = ({ e, taille = 190 }) => {
  const f = useCurrentFrame();
  if (!e) return null;
  return (
    <div style={{ position: "absolute", top: 350, left: G, right: D, display: "flex", justifyContent: "center" }}>
      <Pop><div style={{ fontSize: taille, lineHeight: 1, transform: `rotate(${Math.sin(f / 6) * 6}deg) translateY(${Math.sin(f / 9) * 10}px)`,
        filter: "drop-shadow(0 12px 30px rgba(0,0,0,0.45))" }}>{e}</div></Pop>
    </div>
  );
};

// texte cinétique : chaque mot arrive en ressort, les mots clés en or sur un surligneur
const Cinetique: React.FC<{ texte: string; taille: number; top: number; pas?: number }> = ({ texte, taille, top, pas = 3 }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <div style={{ position: "absolute", top, left: G, right: D, textAlign: "center", fontFamily, fontWeight: 900, fontSize: taille,
      lineHeight: 1.12, color: CREME, textShadow: "0 6px 24px rgba(0,0,0,0.5)" }}>
      {motsCles(texte).map(([m, cle], k) => {
        const p = spring({ frame: f - 2 - k * pas, fps, config: { damping: 12, stiffness: 200, mass: 0.5 } });
        return (
          <span key={k} style={{ display: "inline-block", marginRight: taille * 0.25, transform: `translateY(${(1 - p) * 40}px) scale(${0.7 + 0.3 * p})`,
            opacity: p, color: cle ? NUIT : CREME, background: cle ? OR : "transparent", padding: cle ? "0 14px" : 0, borderRadius: 10 }}>{m}</span>
        );
      })}
    </div>
  );
};

const Accroche: React.FC<{ sc: ScenePerso }> = ({ sc }) => {
  const f = useCurrentFrame();
  const secousse = f < 12 ? Math.sin(f * 2.2) * (12 - f) : 0;
  return (
    <div style={{ transform: `translateX(${secousse}px)` }}>
      <Emoji e={sc.emoji} taille={230} />
      <Cinetique texte={sc.ecran ?? ""} taille={(sc.ecran ?? "").length > 40 ? 84 : 100} top={640} pas={4} />
    </div>
  );
};

const Liste: React.FC<{ sc: ScenePerso; long: number }> = ({ sc, long }) => {
  const brut = sc.ecran ?? "";
  const [titre, reste] = brut.includes(":") ? [brut.split(":")[0], brut.split(":").slice(1).join(":")] : ["", brut];
  const etapes = reste.split("|").map((x) => x.trim().replace(/^\d+\s*[.)-]\s*/, "")).filter(Boolean);
  const pas = Math.max(8, Math.floor((long - 15) / Math.max(1, etapes.length)));
  return (
    <>
      {titre && <Cinetique texte={titre.trim()} taille={64} top={330} />}
      <div style={{ position: "absolute", top: 520, left: G, right: D }}>
        {etapes.map((e, k) => (
          <Pop key={k} delai={6 + k * pas} style={{ transformOrigin: "left center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 26, marginBottom: 36, background: "rgba(255,248,236,0.10)",
              border: "2px solid rgba(255,248,236,0.18)", borderRadius: 24, padding: "22px 26px" }}>
              <div style={{ minWidth: 84, height: 84, borderRadius: 42, background: OR, color: NUIT, fontFamily, fontWeight: 900, fontSize: 50,
                display: "flex", alignItems: "center", justifyContent: "center" }}>{k + 1}</div>
              <div style={{ fontFamily, fontWeight: 800, fontSize: e.length > 26 ? 46 : 54, lineHeight: 1.12, color: CREME }}>{fr(e)}</div>
            </div>
          </Pop>
        ))}
      </div>
    </>
  );
};

// deux barres qui montent : « Perdre 100 » vs « Gagner 100 », valeurs relatives
const Comparaison: React.FC<{ sc: ScenePerso }> = ({ sc }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const va = Math.max(0.1, sc.valeur_a ?? 1), vb = Math.max(0.1, sc.valeur_b ?? 1), max = Math.max(va, vb);
  const barre = (lib: string, v: number, c: string, k: number) => {
    const p = spring({ frame: f - 6 - k * 6, fps, config: { damping: 14, stiffness: 90 } });
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end", width: 300, height: 560 }}>
        <div style={{ fontFamily, fontWeight: 900, fontSize: 56, color: c, marginBottom: 14, opacity: p }}>{`×${Math.round(v * 10) / 10}`}</div>
        <div style={{ width: 220, height: 420 * (v / max) * p, background: c, borderRadius: "22px 22px 6px 6px", boxShadow: `0 0 40px ${c}88` }} />
        <div style={{ fontFamily, fontWeight: 800, fontSize: 42, color: CREME, marginTop: 20, textAlign: "center" }}>{lib}</div>
      </div>
    );
  };
  return (
    <>
      {sc.ecran && <Cinetique texte={sc.ecran} taille={60} top={300} />}
      <div style={{ position: "absolute", top: 470, left: G, right: D, display: "flex", justifyContent: "space-around", alignItems: "flex-end" }}>
        {barre(sc.a ?? "A", va, CORAIL, 0)}
        {barre(sc.b ?? "B", vb, OR, 1)}
      </div>
    </>
  );
};

const Citation: React.FC<{ sc: ScenePerso }> = ({ sc }) => {
  const f = useCurrentFrame();
  const mots = fr(sc.ecran ?? "").replace(/\*/g, "").split(" ");
  const taille = (sc.ecran ?? "").length > 80 ? 66 : 80;
  return (
    <div style={{ position: "absolute", top: 380, left: G + 20, right: D }}>
      <Pop><div style={{ fontFamily: serif, fontSize: 240, color: OR, lineHeight: 0.8, height: 150 }}>“</div></Pop>
      <div style={{ fontFamily: serif, fontStyle: "italic", fontWeight: 700, fontSize: taille, lineHeight: 1.2, color: CREME }}>
        {mots.map((m, k) => (
          <span key={k} style={{ opacity: interpolate(f, [6 + k * 2, 11 + k * 2], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>{m} </span>
        ))}
      </div>
    </div>
  );
};

const Question: React.FC<{ sc: ScenePerso }> = ({ sc }) => (
  <>
    <Emoji e={sc.emoji ?? "💬"} taille={200} />
    <Cinetique texte={sc.ecran ?? ""} taille={(sc.ecran ?? "").length > 60 ? 64 : 76} top={620} />
    <div style={{ position: "absolute", top: 1180, left: G, right: D, display: "flex", justifyContent: "center" }}>
      <Pop delai={14}><div style={{ background: OR, color: NUIT, fontFamily, fontWeight: 900, fontSize: 44, padding: "18px 34px",
        borderRadius: 50 }}>Réponds en commentaire 👇</div></Pop>
    </div>
  </>
);

const Signature: React.FC<{ s: ScriptPerso }> = ({ s }) => (
  <AbsoluteFill style={{ top: 300, height: 900, alignItems: "center", justifyContent: "center", textAlign: "center", paddingRight: D - G }}>
    <Pop><div style={{ fontSize: 150 }}>🧠</div></Pop>
    <Pop delai={4}><div style={{ fontFamily: serif, fontStyle: "italic", fontWeight: 700, fontSize: 96, color: CREME, marginTop: 20 }}>{s.nom}</div></Pop>
    <Pop delai={8}><div style={{ fontFamily, fontWeight: 800, fontSize: 46, color: OR, marginTop: 20 }}>Abonne-toi : {s.compte}</div></Pop>
  </AbsoluteFill>
);

// sous-titres karaoké : 4 mots au plus, le mot prononcé en or
const SousTitres: React.FC<{ sc: ScenePerso }> = ({ sc }) => {
  const f = useCurrentFrame();
  if (!sc.voix || !sc.soustitre || ["citation", "question", "signature"].includes(sc.type)) return null;
  const mots = fr(sc.soustitre).split(/ +/).filter(Boolean);
  const total = mots.reduce((n, m) => n + m.length + 1, 0);
  const images = sc.voix.duree * FPS;
  let t = VOIX_DEBUT, actuel = mots.length - 1;
  for (let k = 0; k < mots.length; k++) { t += images * (mots[k].length + 1) / total; if (f < t) { actuel = k; break; } }
  if (f < VOIX_DEBUT) return null;
  const debut = Math.floor(actuel / 4) * 4;
  return (
    <div style={{ position: "absolute", top: 1150, left: G, right: D, display: "flex", justifyContent: "center", flexWrap: "wrap",
      gap: "6px 22px", fontFamily, fontWeight: 900, fontSize: 58, lineHeight: 1.15, textAlign: "center",
      textShadow: "0 4px 0 #000, 0 0 18px rgba(0,0,0,0.8)" }}>
      {mots.slice(debut, debut + 4).map((m, k) => (
        <span key={k} style={{ color: debut + k === actuel ? OR : CREME, transform: `scale(${debut + k === actuel ? 1.1 : 1})`,
          display: "inline-block" }}>{m}</span>
      ))}
    </div>
  );
};

const Entete: React.FC<{ s: ScriptPerso }> = ({ s }) => (
  <div style={{ position: "absolute", top: 250, left: G, right: D, display: "flex", justifyContent: "center" }}>
    <div style={{ background: "rgba(15,16,32,0.6)", border: `2px solid ${OR}`, color: OR, fontFamily, fontWeight: 800, fontSize: 26,
      letterSpacing: 3, padding: "8px 20px", borderRadius: 40 }}>{s.rubrique.toUpperCase()}</div>
  </div>
);

// entrée de scène : zoom « punch » + flash blanc bref
const Punch: React.FC<{ children: React.ReactNode; long: number }> = ({ children, long }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: f, fps, config: { damping: 14, stiffness: 160 } });
  const sortie = interpolate(f, [long - 4, long], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ transform: `scale(${1.12 - 0.12 * p})`, opacity: sortie }}>
      {children}
      <AbsoluteFill style={{ background: CREME, opacity: interpolate(f, [0, 4], [0.35, 0], { extrapolateRight: "clamp" }), pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};

export const PersoReel: React.FC<ScriptPerso> = (s) => {
  const { scenes, total } = plan(s);
  const f = useCurrentFrame();
  const parole = scenes.filter((p) => p.sc.voix).map((p) => [p.debut + VOIX_DEBUT, p.debut + VOIX_DEBUT + Math.ceil(p.sc.voix!.duree * FPS)]);
  const attenuation = (x: number) => Math.min(1, ...parole.map(([a, b]) =>
    interpolate(x, [a - 8, a, b, b + 8], [1, 0.35, 0.35, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })));
  return (
    <AbsoluteFill style={{ backgroundColor: NUIT, fontFamily }}>
      <Fond />
      {scenes.map((p) => (
        <Sequence key={p.i} from={p.debut} durationInFrames={p.longueur}>
          {p.sc.media && <Media m={p.sc.media} long={p.longueur} />}
          <Punch long={p.longueur}>
            {p.sc.type === "accroche" && <Accroche sc={p.sc} />}
            {p.sc.type === "texte" && <><Emoji e={p.sc.emoji} /><Cinetique texte={p.sc.ecran ?? ""} taille={(p.sc.ecran ?? "").length > 34 ? 74 : 88} top={640} /></>}
            {p.sc.type === "liste" && <Liste sc={p.sc} long={p.longueur} />}
            {p.sc.type === "comparaison" && <Comparaison sc={p.sc} />}
            {p.sc.type === "citation" && <Citation sc={p.sc} />}
            {p.sc.type === "question" && <Question sc={p.sc} />}
            {p.sc.type === "signature" && <Signature s={s} />}
          </Punch>
          <SousTitres sc={p.sc} />
          {p.sc.voix && <Sequence from={VOIX_DEBUT}><Audio src={staticFile(p.sc.voix.src)} /></Sequence>}
        </Sequence>
      ))}
      <Entete s={s} />
      <div style={{ position: "absolute", top: 0, left: 0, height: 10, width: `${(f / total) * 100}%`, background: `linear-gradient(90deg, ${CORAIL}, ${OR})` }} />
      {s.musique && (
        <Audio src={staticFile(s.musique)} loop
          volume={(x) => (s.volume_musique ?? 0.12) * attenuation(x) * interpolate(x, [0, 15, total - 30, total], [0, 1, 1, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      )}
    </AbsoluteFill>
  );
};
