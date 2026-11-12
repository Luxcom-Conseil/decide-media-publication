// Gabarit V3 (27/10/2026, mode information le 02/11/2026) : le rythme des Reels perso aux couleurs DECIDE. Hook, entrée de scène
// « punch », texte cinétique mot à mot (*mots clés* en orange), sous-titres karaoké, fonds réalistes libres (Wikimedia
// Commons, Pixabay) avec leur crédit à l'écran, dessins animés pour un lieu, un chiffre ou une date.
// Zones sûres (1080×1920, Shorts / Reels / TikTok) : rien au-dessus de 230 (barres de recherche et onglets des applis),
// en-tête 230–400, contenu 430–1240, sous-titres 1270–1430, crédit ~1450, rien d'important dans les 150 px de droite.
import React from "react";
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";
import { Dessin, type Illustration } from "./Illustrations";

const { fontFamily } = loadFont("normal", { weights: ["600", "700", "800", "900"], subsets: ["latin", "latin-ext"] });

export const FPS = 30;
const NOIR = "#0E0E0E";
const BLANC = "#FFFFFF";
const ORANGE = "#F26A1B";
const GRIS = "#B4B4BC";
const VOIX_DEBUT = 3, VOIX_FIN = 5; // images : rythme serré
const G = 60, D = 150; // marges gauche / droite

// voile : photo de fond très assombrie derrière un dessin (une image de plus, sans gêner la lecture du dessin)
export type MediaV3 = { src: string; video: boolean; credit?: string; logo?: boolean; voile?: boolean };

export type SceneV3 = {
  type: "accroche" | "media" | "explication" | "outro";
  ecran?: string; // *mot clé* en orange
  illustration?: Illustration;
  media?: MediaV3;
  soustitre?: string;
  voix?: { src: string; duree: number };
  duree?: number;
  tenue?: number; // secondes d'image gardées après la voix : un Short dure 30 s au moins (agent/gabarit_v3.py, etirer)
  // bruitages de la charte sonore (agent/sons.py) : joués à `a` s du début de la scène, avancés de `avance` s
  sons?: { src: string; a: number; avance: number; gain: number }[];
};

export type ScriptV3 = {
  rubrique: string;
  lieu?: string;
  date?: string;
  titre: string;
  image: string; // visuel du lot (affiche DECIDE)
  source?: string;
  scenes: SceneV3[];
  musique?: string;
  volume_musique?: number;
};

const longueur = (sc: SceneV3) => (sc.voix ? VOIX_DEBUT + Math.ceil(sc.voix.duree * FPS) + VOIX_FIN : Math.round((sc.duree ?? 3) * FPS))
  + Math.round((sc.tenue ?? 0) * FPS);

function plan(s: ScriptV3) {
  let t = 0;
  const scenes = s.scenes.map((sc, i) => { const p = { sc, i, debut: t, longueur: longueur(sc) }; t += p.longueur; return p; });
  return { scenes, total: t };
}
export const dureeTotaleV3 = (s: ScriptV3) => plan(s).total;

const fr = (t: string) => t.replace(/ ([?!:;»])/g, " $1").replace(/« /g, "« ");
const estChiffre = (m: string) => /\d|%/.test(m);

// « Le prix *double* en mai » → [["Le", false], ["prix", false], ["double", true], …] ; les chiffres sont toujours clés
function motsCles(t: string): [string, boolean][] {
  const out: [string, boolean][] = [];
  let cle = false;
  for (const m of fr(t).split(" ").filter(Boolean)) {
    const debut = m.startsWith("*"), fin = m.replace(/[.,!?:;»]+$/, "").endsWith("*");
    const mot = m.replace(/\*/g, "");
    out.push([mot, cle || debut || estChiffre(mot)]);
    if (debut && !fin) cle = true;
    if (fin) cle = false;
  }
  return out;
}

// ---------------------------------------------------------------- fonds
const Fond: React.FC = () => {
  const f = useCurrentFrame();
  const halo = (x: number, y: number, r: number, c: string, v: number, o: number) => (
    <div style={{ position: "absolute", left: x + Math.sin(f / v) * 110, top: y + Math.cos(f / (v * 1.3)) * 130, width: r, height: r,
      borderRadius: r, background: c, filter: "blur(130px)", opacity: o }} />
  );
  return (
    <AbsoluteFill style={{ background: `linear-gradient(165deg, #1A1A1F 0%, ${NOIR} 70%)`, overflow: "hidden" }}>
      {halo(-250, 250, 700, ORANGE, 80, 0.35)}
      {halo(650, 1150, 600, "#7A2E08", 100, 0.5)}
    </AbsoluteFill>
  );
};

// photo ou vidéo plein écran, assombrie pour que le texte reste lisible ; un logo est posé sur une carte blanche
const Media: React.FC<{ m: MediaV3; long: number }> = ({ m, long }) => {
  const f = useCurrentFrame();
  if (m.logo) {
    return (
      <>
        <Fond />
        <div style={{ position: "absolute", top: 480, left: 140, width: 800, height: 440, background: BLANC, borderRadius: 28,
          display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 30px 80px rgba(0,0,0,0.5)",
          transform: `scale(${interpolate(f, [0, long], [1, 1.04])})` }}>
          <Img src={staticFile(m.src)} style={{ maxWidth: 680, maxHeight: 340, objectFit: "contain" }} />
        </div>
      </>
    );
  }
  const zoom = interpolate(f, [0, long], [1.04, 1.16]);
  const style: React.CSSProperties = { width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})` };
  return (
    <AbsoluteFill>
      {m.video ? <OffthreadVideo src={staticFile(m.src)} muted style={style} /> : <Img src={staticFile(m.src)} style={style} />}
      <AbsoluteFill style={{ background: m.voile ? "rgba(14,14,14,0.8)"
        : "linear-gradient(180deg, rgba(14,14,14,0.75) 0%, rgba(14,14,14,0.25) 30%, rgba(14,14,14,0.45) 50%, rgba(14,14,14,0.92) 72%)" }} />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- éléments
const Pop: React.FC<{ delai?: number; children: React.ReactNode; style?: React.CSSProperties }> = ({ delai = 0, children, style }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: f - delai, fps, config: { damping: 12, stiffness: 180, mass: 0.6 } });
  return <div style={{ transform: `scale(${0.5 + 0.5 * p})`, opacity: Math.min(1, p * 1.5), ...style }}>{children}</div>;
};

// immediat : tous les mots sont là dès la première image (le hook sert de couverture : TikTok, X et LinkedIn la prennent au début)
const Cinetique: React.FC<{ texte: string; taille: number; top: number; pas?: number; immediat?: boolean }> = ({ texte, taille, top, pas = 3, immediat }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <div style={{ position: "absolute", top, left: G, right: D - 40, textAlign: "center", fontFamily, fontWeight: 900, fontSize: taille,
      lineHeight: 1.14, color: BLANC, textShadow: "0 6px 24px rgba(0,0,0,0.6)" }}>
      {motsCles(texte).map(([m, cle], k) => {
        const p = immediat ? 1 : spring({ frame: f - 2 - k * pas, fps, config: { damping: 12, stiffness: 200, mass: 0.5 } });
        return (
          <span key={k} style={{ display: "inline-block", margin: `0 ${taille * 0.12}px ${taille * 0.12}px`, transform: `translateY(${(1 - p) * 40}px) scale(${0.7 + 0.3 * p})`,
            opacity: p, background: cle ? ORANGE : "transparent", padding: cle ? "0 14px" : 0, borderRadius: 10 }}>{m}</span>
        );
      })}
    </div>
  );
};

// accroche = couverture : le texte est complet dès la première image, en grand, dans la zone que gardent les grilles de
// profil (recadrage 3:4 au centre, y 240–1680) ; sur une vraie photo si on en a une, sinon sur le visuel du lot en carte
const Accroche: React.FC<{ sc: SceneV3; image: string; long: number }> = ({ sc, image, long }) => {
  const f = useCurrentFrame();
  const t = sc.ecran ?? "";
  if (sc.media) {
    // un logo occupe la carte blanche 480–920 : l'accroche passe dessous
    return <Cinetique texte={t} taille={sc.media.logo ? 76 : t.length > 50 ? 84 : 100} top={sc.media.logo ? 960 : 700} immediat />;
  }
  return (
    <>
      <div style={{ position: "absolute", top: 430, left: 260, width: 560, height: 560, borderRadius: 24, overflow: "hidden", border: `6px solid ${ORANGE}`,
        boxShadow: "0 30px 80px rgba(0,0,0,0.6)" }}>
        <Img src={staticFile(image)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${interpolate(f, [0, long], [1, 1.06])})` }} />
      </div>
      <Cinetique texte={t} taille={t.length > 50 ? 66 : 78} top={1020} immediat />
    </>
  );
};

const Explication: React.FC<{ sc: SceneV3; image: string }> = ({ sc, image }) => (
  <>
    <div style={{ position: "absolute", top: 510, left: 140 }}>
      {sc.illustration?.type === "photo"
        ? <div style={{ position: "relative", width: 760, height: 500, borderRadius: 20, overflow: "hidden", border: `6px solid ${ORANGE}` }}>
            {/* la partie photo du visuel seulement (sous le logo, au-dessus du titre : 8 à 48 % de sa hauteur), le titre est déjà en tête */}
            <Img src={staticFile(image)} style={{ position: "absolute", width: 1250, height: 1250, maxWidth: "none", left: -245, top: -100 }} /></div>
        : <Dessin il={sc.illustration!} />}
    </div>
    {sc.ecran && <Cinetique texte={sc.ecran} taille={sc.ecran.length > 28 ? 60 : 70} top={1040} />}
  </>
);

const ScMedia: React.FC<{ sc: SceneV3 }> = ({ sc }) => (
  <>
    {sc.ecran && <Cinetique texte={sc.ecran} taille={sc.ecran.length > 28 ? 74 : 88} top={sc.media?.logo ? 1000 : 820} />}
  </>
);

const Outro: React.FC<{ s: ScriptV3 }> = ({ s }) => (
  <AbsoluteFill style={{ top: 420, height: 800, alignItems: "center", justifyContent: "center", textAlign: "center" }}>
    <Pop><div style={{ fontFamily, fontWeight: 900, fontSize: 120, color: BLANC }}>DEC<span style={{ color: ORANGE }}>I</span>DE
      <span style={{ fontWeight: 600, fontSize: 50, marginLeft: 8 }}>media</span></div></Pop>
    <Pop delai={4}><div style={{ fontFamily, fontWeight: 800, fontSize: 52, color: ORANGE, marginTop: 20 }}>Abonne-toi</div></Pop>
    {s.source && <Pop delai={8}><div style={{ fontFamily, fontWeight: 600, fontSize: 30, color: GRIS, marginTop: 50, padding: "0 80px" }}>{s.source}</div></Pop>}
  </AbsoluteFill>
);

// sous-titres karaoké : 4 mots au plus, le mot prononcé en orange
const SousTitres: React.FC<{ sc: SceneV3 }> = ({ sc }) => {
  const f = useCurrentFrame();
  // le hook est déjà écrit en grand : ses sous-titres le doubleraient, couverture comprise
  if (!sc.voix || !sc.soustitre || sc.type === "outro" || sc.type === "accroche") return null;
  const mots = fr(sc.soustitre).split(/ +/).filter(Boolean); // l'espace insécable lie un nombre à son unité
  const total = mots.reduce((n, m) => n + m.length + 1, 0);
  const images = sc.voix.duree * FPS;
  let t = VOIX_DEBUT, actuel = mots.length - 1;
  for (let k = 0; k < mots.length; k++) { t += images * (mots[k].length + 1) / total; if (f < t) { actuel = k; break; } }
  if (f < VOIX_DEBUT) return null;
  const debut = Math.floor(actuel / 4) * 4;
  return (
    <div style={{ position: "absolute", top: 1270, left: G, right: D - 40, display: "flex", justifyContent: "center", flexWrap: "wrap",
      gap: "6px 22px", fontFamily, fontWeight: 900, fontSize: 58, lineHeight: 1.15, textAlign: "center",
      textShadow: "0 4px 0 #000, 0 0 18px rgba(0,0,0,0.85)" }}>
      {/* le mot prononcé change de couleur seulement : agrandi, il mangeait l'espace avec ses voisins */}
      {mots.slice(debut, debut + 4).map((m, k) => (
        <span key={k} style={{ color: debut + k === actuel ? ORANGE : BLANC }}>{m}</span>
      ))}
    </div>
  );
};

// crédit obligatoire des images libres (auteur, licence), ou la source de l'article sur les scènes sans média
const Credit: React.FC<{ texte?: string }> = ({ texte }) => texte ? (
  <div style={{ position: "absolute", top: 1450, left: G, right: D, display: "flex" }}>
    <div style={{ background: "rgba(14,14,14,0.7)", color: GRIS, fontFamily, fontWeight: 600, fontSize: 22, padding: "5px 12px", borderRadius: 6 }}>{texte}</div>
  </div>
) : null;

const Entete: React.FC<{ s: ScriptV3 }> = ({ s }) => (
  <div style={{ position: "absolute", top: 230, left: G, right: G }}>
    <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
      <div style={{ background: ORANGE, color: BLANC, fontFamily, fontWeight: 800, fontSize: 26, letterSpacing: 2, padding: "7px 16px", borderRadius: 6 }}>{s.rubrique}</div>
      <div style={{ flex: 1, color: GRIS, fontFamily, fontWeight: 700, fontSize: 26, letterSpacing: 1, textShadow: "0 2px 8px #000" }}>
        {[s.lieu, s.date].filter(Boolean).join(" · ").toUpperCase()}</div>
      <div style={{ width: 66, height: 66, borderRadius: 12, background: BLANC, display: "flex", alignItems: "center", justifyContent: "center",
        fontFamily, fontWeight: 900, fontSize: 46, color: NOIR }}>D<span style={{ color: ORANGE }}>.</span></div>
    </div>
    <div style={{ marginTop: 18, fontFamily, fontWeight: 800, fontSize: s.titre.length > 45 ? 38 : 44, lineHeight: 1.15, color: BLANC,
      textShadow: "0 3px 12px rgba(0,0,0,0.9)", paddingRight: 60 }}>{fr(s.titre)}</div>
  </div>
);

// entrée de scène : zoom « punch » + flash bref, sortie en fondu court
// première scène : pas d'entrée, la première image est déjà la couverture
const Punch: React.FC<{ children: React.ReactNode; long: number; premiere?: boolean }> = ({ children, long, premiere }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = premiere ? 1 : spring({ frame: f, fps, config: { damping: 14, stiffness: 160 } });
  const sortie = interpolate(f, [long - 4, long], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ transform: `scale(${1.1 - 0.1 * p})`, opacity: sortie }}>
      {children}
      {!premiere && <AbsoluteFill style={{ background: ORANGE, opacity: interpolate(f, [0, 4], [0.28, 0], { extrapolateRight: "clamp" }), pointerEvents: "none" }} />}
    </AbsoluteFill>
  );
};

export const GabaritV3: React.FC<ScriptV3> = (s) => {
  const { scenes, total } = plan(s);
  const f = useCurrentFrame();
  const parole = scenes.filter((p) => p.sc.voix).map((p) => [p.debut + VOIX_DEBUT, p.debut + VOIX_DEBUT + Math.ceil(p.sc.voix!.duree * FPS)]);
  const attenuation = (x: number) => Math.min(1, ...parole.map(([a, b]) =>
    interpolate(x, [a - 8, a, b, b + 8], [1, 0.35, 0.35, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })));
  return (
    <AbsoluteFill style={{ backgroundColor: NOIR, fontFamily }}>
      <Fond />
      {scenes.map((p) => (
        <Sequence key={p.i} from={p.debut} durationInFrames={p.longueur}>
          <Punch long={p.longueur} premiere={p.i === 0}>
            {p.sc.media && <Media m={p.sc.media} long={p.longueur} />}
            {p.sc.type === "accroche" && <Accroche sc={p.sc} image={s.image} long={p.longueur} />}
            {p.sc.type === "media" && <ScMedia sc={p.sc} />}
            {p.sc.type === "explication" && <Explication sc={p.sc} image={s.image} />}
            {p.sc.type === "outro" && <Outro s={s} />}
          </Punch>
          <SousTitres sc={p.sc} />
          <Credit texte={p.sc.media?.credit} />
          {p.sc.voix && <Sequence from={VOIX_DEBUT}><Audio src={staticFile(p.sc.voix.src)} /></Sequence>}
        </Sequence>
      ))}
      {scenes.flatMap((p) => (p.sc.sons ?? []).map((b, k) => {
        const debut = p.debut + Math.round((b.a - b.avance) * FPS);
        return (
          <Sequence key={`son-${p.i}-${k}`} from={Math.max(0, debut)}>
            <Audio src={staticFile(b.src)} volume={b.gain} trimBefore={Math.max(0, -debut)} />
          </Sequence>
        );
      }))}
      <Entete s={s} />
      <div style={{ position: "absolute", top: 0, left: 0, height: 10, width: `${(f / total) * 100}%`, background: ORANGE }} />
      {s.musique && (
        <Audio src={staticFile(s.musique)} loop
          volume={(x) => (s.volume_musique ?? 0.10) * attenuation(x) * interpolate(x, [0, 15, total - 30, total], [0, 1, 1, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      )}
    </AbsoluteFill>
  );
};
