// Rubrique actu de « Histoires vraies d'argent » (agent/actu.py), habillage « décryptage » demandé par Stéphane le
// 19/11/2026 d'après des vidéos d'enquête qu'il aime : image en haut, fond sombre en bas ; grandes cartes en capitales
// (blanc + mot clé jaune, étiquette jaune au-dessus) ; fiche nom (nom, rôle sur pastille rouge, détail encadré) ;
// tampons penchés ; chiffres géants ; barres de comparaison « ce qu'on dit / la réalité » ; listes cochées ; voix
// sous-titrée 2 ou 3 mots à la fois en capitales ; ligne SOURCE en bas de chaque scène ; fil d'indices qui se remplit.
// Zones sûres TikTok (1080×1920) : rien d'important au-dessus de 230, sous 1400, ni dans les 150 px de droite.
import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";
import { loadFont as loadAnton } from "@remotion/google-fonts/Anton";
import { loadFont as loadMono } from "@remotion/google-fonts/SpaceMono";
import { FPS } from "./RecitReel";

const { fontFamily } = loadFont("normal", { weights: ["600", "700", "800", "900"], subsets: ["latin", "latin-ext"] });
const { fontFamily: anton } = loadAnton("normal", { weights: ["400"], subsets: ["latin", "latin-ext"] });
const { fontFamily: mono } = loadMono("normal", { weights: ["400", "700"], subsets: ["latin", "latin-ext"] });

const NOIR = "#0E0E10";
const BLANC = "#FFFFFF";
const JAUNE = "#FFD21F";
const ROUGE = "#E5262B";
const GRIS = "#9A9AA2";
const G = 60, D = 150;

export type Barre = { texte: string; valeur?: string | null; mauvais?: boolean | null };
export type SceneActu = {
  type: "accroche" | "recit" | "date" | "chiffre" | "lecon" | "question" | "signature";
  carte?: "titre" | "nom" | "tampon" | "chiffre" | "barres" | "liste" | "citation" | "date" | "image" | null;
  ecran?: string | null;   // *mot clé* en jaune
  grand?: string | null;   // chiffre ou date
  label?: string | null;   // étiquette jaune au-dessus de la carte
  detail?: string | null;  // pastille rouge (rôle, qui parle) ou ligne sous la carte
  items?: Barre[] | null;
  accent?: string | null;  // mots de la voix à mettre en jaune dans les sous-titres
  source?: string | null;  // « franceinfo · 19/11/2026 »
  indice?: number | null;  // case du fil révélée à cette scène
  image?: { src: string; credit: string };
  soustitre?: string;
  voix?: { src: string; duree: number };
  duree?: number;
  sons?: { src: string; a: number; avance: number; gain: number }[];
};

export type ScriptActu = {
  serie: string;
  titre: string;
  compte: string;
  partie?: string | null;
  slogan?: string | null;
  fil_titre?: string | null;
  fil?: string[] | null;
  scenes: SceneActu[];
  musique?: string;
  volume_musique?: number;
};

const longueur = (sc: SceneActu) => sc.voix ? Math.ceil(sc.voix.duree * FPS) : Math.round((sc.duree ?? 3) * FPS);
function plan(s: ScriptActu) {
  let t = 0;
  const scenes = s.scenes.map((sc, i) => { const p = { sc, i, debut: t, longueur: longueur(sc) }; t += p.longueur; return p; });
  return { scenes, total: t };
}
export const dureeTotaleActu = (s: ScriptActu) => plan(s).total;

const fr = (t: string) => t.replace(/ ([?!:;»])/g, " $1").replace(/« /g, "« ");
const MAJ = (t: string) => fr(t).toLocaleUpperCase("fr-FR");

// texte avec *mots clés* en jaune, en capitales
const Cles: React.FC<{ texte: string; couleur?: string }> = ({ texte, couleur = BLANC }) => {
  let cle = false;
  return (
    <>
      {MAJ(texte).split(" ").filter(Boolean).map((m, k) => {
        const debut = m.startsWith("*"), fin = m.replace(/[.,!?:;»]+$/, "").endsWith("*");
        const jaune = cle || debut;
        if (debut && !fin) cle = true;
        if (fin) cle = false;
        return <span key={k} style={{ color: jaune ? JAUNE : couleur }}>{m.replace(/\*/g, "")} </span>;
      })}
    </>
  );
};

const useApparition = (retard = 2) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: f - retard, fps, config: { damping: 13, stiffness: 190, mass: 0.6 } });
};

// ---------------------------------------------------------------- fond : image en haut, fondue dans le noir
const Fond: React.FC<{ im?: SceneActu["image"]; long: number; i: number; fige?: boolean }> = ({ im, long, i, fige }) => {
  const f = useCurrentFrame();
  if (!im) return <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 30%, #23232A 0%, ${NOIR} 70%)` }} />;
  const z = fige ? 1.05 : interpolate(f, [0, long], i % 2 === 0 ? [1.03, 1.12] : [1.12, 1.03]);
  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: NOIR }}>
      <Img src={staticFile(im.src)} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover",
        filter: "blur(40px) brightness(0.35)", transform: "scale(1.3)" }} />
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 1250, overflow: "hidden" }}>
        <Img src={staticFile(im.src)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${z})` }} />
      </div>
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(14,14,16,0.55) 0%, rgba(14,14,16,0.05) 16%, " +
        "rgba(14,14,16,0.25) 40%, rgba(14,14,16,0.75) 58%, rgba(14,14,16,0.97) 66%, rgba(14,14,16,1) 100%)" }} />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- éléments de cartes
const Etiquette: React.FC<{ t: string; fond?: string; couleur?: string; taille?: number }> = ({ t, fond = JAUNE, couleur = NOIR, taille = 30 }) => (
  <span style={{ display: "inline-block", background: fond, color: couleur, fontFamily, fontWeight: 900, fontSize: taille,
    padding: "6px 16px", borderRadius: 4, letterSpacing: 1 }}>{MAJ(t)}</span>
);
const Encadre: React.FC<{ t: string }> = ({ t }) => (
  <span style={{ display: "inline-block", border: `2px solid ${JAUNE}`, color: JAUNE, fontFamily: mono, fontWeight: 700, fontSize: 24,
    padding: "4px 14px", letterSpacing: 1, background: "rgba(14,14,16,0.6)" }}>{MAJ(t)}</span>
);
const Zone: React.FC<{ top: number; children: React.ReactNode }> = ({ top, children }) => {
  const p = useApparition();
  return (
    <div style={{ position: "absolute", top, left: G, right: D - 40, textAlign: "center", display: "flex", flexDirection: "column",
      alignItems: "center", gap: 18, transform: `translateY(${(1 - p) * 30}px) scale(${0.94 + 0.06 * p})`, opacity: p }}>{children}</div>
  );
};
const Gros: React.FC<{ t: string; taille?: number }> = ({ t, taille }) => {
  const n = t.replace(/\*/g, "").length;
  const s = taille ?? (n > 60 ? 64 : n > 40 ? 76 : n > 22 ? 90 : 108);
  return (
    <div style={{ fontFamily, fontWeight: 900, fontSize: s, lineHeight: 1.06, letterSpacing: -1,
      textShadow: "0 4px 0 rgba(0,0,0,0.55), 0 0 30px rgba(0,0,0,0.7)" }}><Cles texte={t} /></div>
  );
};

const Tampon: React.FC<{ t: string; rouge?: boolean; detail?: string | null; top?: number }> = ({ t, rouge = true, detail, top = 560 }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: f - 2, fps, config: { damping: 9, stiffness: 230, mass: 0.7 } });
  const c = rouge ? ROUGE : JAUNE;
  return (
    <div style={{ position: "absolute", top, left: G, right: D - 40, display: "flex", flexDirection: "column", alignItems: "center", gap: 26 }}>
      <div style={{ transform: `rotate(-7deg) scale(${2 - p})`, opacity: Math.min(1, p * 1.5), border: `9px solid ${c}`, color: c,
        fontFamily: anton, fontSize: t.length > 14 ? 92 : 120, lineHeight: 1, padding: "10px 30px", borderRadius: 10,
        background: rouge ? "rgba(14,14,16,0.35)" : JAUNE, ...(rouge ? {} : { color: NOIR }), letterSpacing: 2 }}>{MAJ(t.replace(/\*/g, ""))}</div>
      {detail && <Encadre t={detail} />}
    </div>
  );
};

const Barres: React.FC<{ items: Barre[]; label?: string | null }> = ({ items, label }) => {
  const f = useCurrentFrame();
  const nums = items.map((b) => parseFloat((b.valeur ?? "").replace(/\s/g, "").replace(",", ".").replace(/[^\d.-]/g, "")) || 0);
  const max = Math.max(...nums.map(Math.abs), 1);
  return (
    <div style={{ position: "absolute", top: 470, left: G + 20, right: D, display: "flex", flexDirection: "column", gap: 26 }}>
      {label && <div style={{ textAlign: "center" }}><Etiquette t={label} /></div>}
      {items.slice(0, 4).map((b, k) => {
        const p = interpolate(f, [6 + k * 8, 22 + k * 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        const larg = nums[k] ? Math.max(8, (Math.abs(nums[k]) / max) * 100) : 100;
        return (
          <div key={k} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ fontFamily, fontWeight: 800, fontSize: 32, color: b.mauvais ? JAUNE : BLANC }}>{MAJ(b.texte)}</div>
            <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
              <div style={{ height: 52, width: `${larg * 0.72 * p}%`, background: b.mauvais ? ROUGE : k === 0 ? JAUNE : GRIS }} />
              <div style={{ fontFamily: anton, fontSize: 52, color: b.mauvais ? ROUGE : BLANC, opacity: p }}>{b.valeur ?? ""}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

const Liste: React.FC<{ items: Barre[]; label?: string | null }> = ({ items, label }) => {
  const f = useCurrentFrame();
  return (
    <div style={{ position: "absolute", top: 470, left: G + 20, right: D, display: "flex", flexDirection: "column", gap: 22 }}>
      {label && <div style={{ textAlign: "center" }}><Encadre t={label} /></div>}
      {items.slice(0, 5).map((b, k) => {
        const p = interpolate(f, [4 + k * 9, 12 + k * 9], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        return (
          <div key={k} style={{ display: "flex", alignItems: "center", gap: 20, opacity: p, transform: `translateX(${(1 - p) * -40}px)` }}>
            <div style={{ width: 54, height: 54, flex: "none", background: b.mauvais ? ROUGE : JAUNE, color: b.mauvais ? BLANC : NOIR,
              fontFamily, fontWeight: 900, fontSize: 38, display: "flex", alignItems: "center", justifyContent: "center" }}>{b.mauvais ? "✕" : k + 1}</div>
            <div style={{ fontFamily, fontWeight: 800, fontSize: 38, color: BLANC, lineHeight: 1.1 }}>{MAJ(b.texte)}
              {b.valeur && <span style={{ color: JAUNE }}> {b.valeur}</span>}</div>
          </div>
        );
      })}
    </div>
  );
};

const Carte: React.FC<{ sc: SceneActu; s: ScriptActu }> = ({ sc, s }) => {
  const ecran = sc.ecran ?? "";
  const indice = sc.indice != null && s.fil && sc.indice >= 0 && sc.indice < s.fil.length
    ? `${(s.fil_titre ?? "indice").replace(/s$/i, "")} ${sc.indice + 1}/${s.fil.length}` : null;
  switch (sc.carte) {
    case "nom":
      return (
        <Zone top={600}>
          {(indice || sc.label) && <Encadre t={sc.label ?? indice!} />}
          <Gros t={ecran} taille={ecran.length > 22 ? 78 : 96} />
          {sc.detail && <Etiquette t={sc.detail} fond={ROUGE} couleur={BLANC} taille={28} />}
          {sc.grand && <Encadre t={sc.grand} />}
        </Zone>
      );
    case "tampon":
      return <Tampon t={ecran} rouge={!/^\s*(vrai|oui)/i.test(ecran)} detail={sc.detail ?? sc.label} />;
    case "chiffre":
      return (
        <Zone top={470}>
          {sc.label && <Etiquette t={sc.label} />}
          <div style={{ fontFamily: anton, color: JAUNE, lineHeight: 1, fontSize: (sc.grand ?? "").length > 10 ? 150 : (sc.grand ?? "").length > 6 ? 200 : 260,
            textShadow: "0 8px 30px rgba(0,0,0,0.7)" }}>{sc.grand}</div>
          {ecran && <Gros t={ecran} taille={54} />}
          {sc.detail && <Etiquette t={sc.detail} fond="#FFFFFF" couleur={NOIR} taille={26} />}
        </Zone>
      );
    case "barres":
      return <Barres items={sc.items ?? []} label={sc.label ?? ecran} />;
    case "liste":
      return <Liste items={sc.items ?? []} label={sc.label ?? ecran} />;
    case "citation":
      return (
        <Zone top={560}>
          <Gros t={`« ${ecran.replace(/^«\s*|\s*»$/g, "")} »`} />
          {sc.detail && <Etiquette t={sc.detail} fond={ROUGE} couleur={BLANC} taille={28} />}
        </Zone>
      );
    case "date":
      return (
        <>
          <div style={{ position: "absolute", top: 330, left: G, fontFamily, fontWeight: 600, fontSize: 52, color: BLANC,
            borderBottom: `4px solid ${JAUNE}`, paddingBottom: 4, textShadow: "0 2px 12px rgba(0,0,0,0.8)" }}>{sc.grand}</div>
          {ecran && <Zone top={640}><Gros t={ecran} taille={72} /></Zone>}
        </>
      );
    case "image":
      return null;
    default: // titre
      return (
        <Zone top={sc.label ? 520 : 580}>
          {sc.label && <Etiquette t={sc.label} />}
          <Gros t={ecran} />
          {sc.detail && <Encadre t={sc.detail} />}
        </Zone>
      );
  }
};

// ---------------------------------------------------------------- voix sous-titrée : 2 ou 3 mots, capitales
const SousTitres: React.FC<{ sc: SceneActu }> = ({ sc }) => {
  const f = useCurrentFrame();
  if (!sc.voix || !sc.soustitre || ["question", "signature"].includes(sc.type)) return null;
  const mots = fr(sc.soustitre).split(/ +/).filter(Boolean).reduce<string[]>((l, m) => {
    if (/^[?!:;»]+$/.test(m) && l.length) l[l.length - 1] += " " + m; else l.push(m);
    return l;
  }, []);
  // groupes de 3 mots (2 si les mots sont longs), coupés après une ponctuation
  const groupes: string[][] = [];
  let g: string[] = [];
  for (const m of mots) {
    g.push(m);
    const long = g.join(" ").length;
    if (g.length >= 3 || long > 18 || /[.,!?:;]$/.test(m)) { groupes.push(g); g = []; }
  }
  if (g.length) groupes.push(g);
  const total = mots.reduce((n, m) => n + m.length + 1, 0);
  const images = sc.voix.duree * FPS;
  let t = 0, actuel = groupes.length - 1;
  for (let k = 0; k < groupes.length; k++) {
    t += images * groupes[k].reduce((n, m) => n + m.length + 1, 0) / total;
    if (f < t) { actuel = k; break; }
  }
  const accents = new Set((sc.accent ?? "").toLocaleLowerCase("fr-FR").split(/[\s,]+/).filter((w) => w.length > 1));
  const jaune = (m: string) => {
    const nu = m.toLocaleLowerCase("fr-FR").replace(/[.,!?:;«»"()]/g, "");
    return accents.has(nu) || /\d/.test(nu);
  };
  return (
    <div style={{ position: "absolute", top: 1170, left: G, right: D - 60, textAlign: "center", fontFamily, fontWeight: 900, fontSize: 62,
      lineHeight: 1.1, textShadow: "0 4px 0 #000, 0 0 20px rgba(0,0,0,0.9)" }}>
      {groupes[actuel].map((m, k) => <span key={k} style={{ color: jaune(m) ? JAUNE : BLANC }}>{MAJ(m)} </span>)}
    </div>
  );
};

// ---------------------------------------------------------------- bas de l'écran : source et fil d'indices
const Source: React.FC<{ sc: SceneActu }> = ({ sc }) => {
  const t = [sc.source ? `SOURCE · ${sc.source}` : "", sc.image?.credit ? `IMAGE · ${sc.image.credit}` : ""].filter(Boolean).join("   ");
  return t ? <div style={{ position: "absolute", top: 1305, left: G, right: D - 40, fontFamily: mono, fontSize: 19, color: GRIS,
    whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{MAJ(t)}</div> : null;
};

const Fil: React.FC<{ s: ScriptActu; revele: number }> = ({ s, revele }) => {
  if (!s.fil || !s.fil.length) return null;
  return (
    <div style={{ position: "absolute", top: 1345, left: G, right: D - 40, display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{ fontFamily: mono, fontWeight: 700, fontSize: 20, color: GRIS, marginRight: 6 }}>{MAJ(s.fil_titre ?? "Indices")}</div>
      {s.fil.slice(0, 5).map((m, k) => (
        <div key={k} style={{ flex: 1, height: 36, display: "flex", alignItems: "center", justifyContent: "center", fontFamily, fontWeight: 900,
          fontSize: 18, background: k <= revele ? JAUNE : "transparent", color: k <= revele ? NOIR : GRIS,
          border: `2px solid ${k <= revele ? JAUNE : "#3A3A42"}`, overflow: "hidden", whiteSpace: "nowrap" }}>{k <= revele ? MAJ(m) : "?"}</div>
      ))}
    </div>
  );
};

const Entete: React.FC<{ s: ScriptActu }> = ({ s }) => (
  <div style={{ position: "absolute", top: 236, left: G, right: D, display: "flex", alignItems: "center", gap: 14 }}>
    <div style={{ width: 54, height: 54, background: JAUNE, color: NOIR, fontFamily: anton, fontSize: 30, display: "flex",
      alignItems: "center", justifyContent: "center" }}>HV</div>
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <div style={{ fontFamily, fontWeight: 900, fontSize: 26, color: BLANC, letterSpacing: 1, textShadow: "0 2px 8px rgba(0,0,0,0.8)" }}>{MAJ(s.serie)}</div>
      <div style={{ fontFamily: mono, fontWeight: 700, fontSize: 19, color: JAUNE, letterSpacing: 1, textShadow: "0 2px 8px rgba(0,0,0,0.8)" }}>
        {MAJ(`Décryptage · ${s.partie ?? "Actu"}`)}</div>
    </div>
  </div>
);

const Question: React.FC<{ sc: SceneActu }> = ({ sc }) => (
  <Zone top={560}>
    <Gros t={sc.ecran ?? ""} taille={(sc.ecran ?? "").length > 50 ? 70 : 84} />
    <Etiquette t="Dis-le en commentaire 👇" taille={40} />
  </Zone>
);

const Signature: React.FC<{ s: ScriptActu }> = ({ s }) => (
  <AbsoluteFill style={{ textAlign: "center" }}>
    <Tampon t="Décrypté" rouge={false} top={440} />
    <div style={{ position: "absolute", top: 700, left: G, right: D - 40, display: "flex", flexDirection: "column", alignItems: "center", gap: 22 }}>
      <div style={{ fontFamily, fontWeight: 900, fontSize: 72, color: BLANC, lineHeight: 1.05 }}>{MAJ(s.serie)}</div>
      <div style={{ fontFamily, fontWeight: 800, fontSize: 40, color: JAUNE }}>{s.slogan ?? "L'actu de ton argent, décryptée chaque jour"}</div>
      <div style={{ fontFamily: mono, fontWeight: 700, fontSize: 32, color: BLANC, opacity: 0.85 }}>{s.compte}</div>
    </div>
  </AbsoluteFill>
);

const Lecon: React.FC<{ sc: SceneActu }> = ({ sc }) => (
  <Zone top={500}>
    <Etiquette t={sc.label ?? "À retenir"} />
    <Gros t={sc.ecran ?? ""} taille={(sc.ecran ?? "").length > 60 ? 64 : 78} />
  </Zone>
);

export type CouvertureActu = { serie: string; accroche: string; image?: { src: string; credit: string } | null; partie?: string | null; compte: string; label?: string | null };

export const ActuCouverture: React.FC<CouvertureActu> = (c) => (
  <AbsoluteFill style={{ backgroundColor: NOIR }}>
    <Fond im={c.image ?? undefined} long={30} i={0} fige />
    <Entete s={{ serie: c.serie, partie: c.partie, titre: "", compte: c.compte, scenes: [] }} />
    <div style={{ position: "absolute", top: 560, left: G, right: D - 40, textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: 18 }}>
      {c.label && <Etiquette t={c.label} />}
      <Gros t={c.accroche} />
    </div>
  </AbsoluteFill>
);

export const ActuReel: React.FC<ScriptActu> = (s) => {
  const { scenes, total } = plan(s);
  const f = useCurrentFrame();
  const parole = scenes.filter((p) => p.sc.voix).map((p) => [p.debut, p.debut + Math.ceil(p.sc.voix!.duree * FPS)]);
  const attenuation = (x: number) => Math.min(1, ...parole.map(([a, b]) =>
    interpolate(x, [a - 8, a, b, b + 8], [1, 0.35, 0.35, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })));
  const courante = scenes.find((p) => f >= p.debut && f < p.debut + p.longueur) ?? scenes[scenes.length - 1];
  const revele = Math.max(-1, ...scenes.filter((p) => p.debut <= f && p.sc.indice != null).map((p) => p.sc.indice as number));
  return (
    <AbsoluteFill style={{ backgroundColor: NOIR }}>
      {scenes.map((p) => (
        <Sequence key={p.i} from={p.debut} durationInFrames={p.longueur}>
          <Fond im={p.sc.image} long={p.longueur} i={p.i} />
          {p.sc.type === "question" ? <Question sc={p.sc} /> : p.sc.type === "signature" ? <Signature s={s} />
            : p.sc.type === "lecon" ? <Lecon sc={p.sc} /> : <Carte sc={p.sc} s={s} />}
          <SousTitres sc={p.sc} />
          {p.sc.type !== "signature" && <Source sc={p.sc} />}
          {p.sc.voix && <Audio src={staticFile(p.sc.voix.src)} />}
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
      {courante.sc.type !== "signature" && <Fil s={s} revele={revele} />}
      <div style={{ position: "absolute", top: 0, left: 0, height: 8, width: `${(f / total) * 100}%`, background: JAUNE }} />
      {s.musique && (
        <Audio src={staticFile(s.musique)} loop
          volume={(x) => (s.volume_musique ?? 0.1) * attenuation(x) * interpolate(x, [0, 15, total - 30, total], [0, 1, 1, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      )}
    </AbsoluteFill>
  );
};
