// Personnages récurrents DECIDE : la même commerçante, le même artisan, le même salarié, la même étudiante d'une vidéo
// à l'autre. Dessin plat (orange, blanc, gris, noir ; pas de dégradé), visage expressif, geste animé.
// Repère : zone 760×500, personnage centré sur x = cx (380 par défaut), pieds en bas (y = 440).
import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";

const { fontFamily } = loadFont("normal", { weights: ["700", "900"], subsets: ["latin", "latin-ext"] });
const O = "#F26A1B", B = "#FFFFFF", N = "#0E0E0E", G = "#4A4A52", GC = "#9A9AA2", TRAIT = "#2A1810";

export type Personnage = "commercante" | "artisan" | "salarie" | "etudiante";
export type Expression = "contente" | "inquiete" | "surprise" | "pensive";
export type Geste = "salue" | "montre" | "reflechit" | "tient_billet" | "tient_document" | "repos";

const PEAU: Record<Personnage, string> = { commercante: "#6B3E26", artisan: "#8A5A3C", salarie: "#4E2E1C", etudiante: "#7A4A2E" };
const HABIT: Record<Personnage, string> = { commercante: O, artisan: G, salarie: G, etudiante: B };
export const NOMS: Record<Personnage, string> = { commercante: "Commerçante", artisan: "Artisan", salarie: "Salarié", etudiante: "Étudiante" };

type P = [number, number];
// bras : épaule → coude → main, au repos et pour chaque geste (bras droit à l'écran)
const REPOS_D: [P, P] = [[462, 320], [470, 398]];
const BRAS_D: Record<Geste, [P, P]> = {
  repos: REPOS_D,
  salue: [[505, 196], [528, 118]],
  montre: [[530, 246], [612, 236]],
  reflechit: [[470, 296], [404, 214]],
  tient_billet: [[486, 312], [546, 292]],
  tient_document: [[486, 312], [546, 292]],
};
const REPOS_G: [P, P] = [[298, 320], [290, 398]];
const JOUE_G: [P, P] = [[284, 296], [328, 196]]; // main sur la joue : inquiétude

const mix = (a: P, b: P, t: number): P => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];

const Bras: React.FC<{ epaule: P; coude: P; main: P; manche: string; peau: string }> = ({ epaule, coude, main, manche, peau }) => (
  <g>
    <path d={`M ${epaule[0]} ${epaule[1]} L ${coude[0]} ${coude[1]} L ${main[0]} ${main[1]}`} fill="none" stroke={manche} strokeWidth={34}
      strokeLinecap="round" strokeLinejoin="round" />
    <path d={`M ${epaule[0]} ${epaule[1]} L ${coude[0]} ${coude[1]} L ${main[0]} ${main[1]}`} fill="none" stroke={N} strokeOpacity={0.15}
      strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" />
    <circle cx={main[0]} cy={main[1]} r={17} fill={peau} />
  </g>
);

const Cheveux: React.FC<{ qui: Personnage }> = ({ qui }) => {
  if (qui === "commercante") return ( // foulard noué, motif wax
    <g>
      <path d="M 314 142 Q 298 70 380 58 Q 466 60 448 142 Q 420 108 380 110 Q 340 108 314 142 Z" fill={O} />
      {[[350, 84], [380, 76], [410, 84], [336, 110], [424, 110], [366, 98], [396, 98]].map(([x, y], k) =>
        <circle key={k} cx={x} cy={y} r={5} fill={B} />)}
      <path d="M 432 70 Q 470 52 476 82 Q 458 92 440 86 Z" fill={O} stroke={B} strokeWidth={3} />
      <circle cx={320} cy={182} r={6} fill={O} />
    </g>
  );
  if (qui === "artisan") return ( // casquette
    <g>
      <path d="M 318 122 Q 320 76 380 76 Q 440 76 442 122 Z" fill={B} />
      <path d="M 380 112 L 486 114 Q 478 126 380 124 Z" fill={O} />
      <rect x={372} y={76} width={16} height={10} rx={4} fill={O} />
    </g>
  );
  if (qui === "salarie") return <path d="M 320 142 Q 318 84 380 84 Q 442 84 440 142 Q 432 112 380 108 Q 328 112 320 142 Z" fill={TRAIT} />;
  return ( // étudiante : deux macarons
    <g>
      <circle cx={328} cy={96} r={30} fill={TRAIT} />
      <circle cx={432} cy={96} r={30} fill={TRAIT} />
      <path d="M 320 144 Q 318 88 380 88 Q 442 88 440 144 Q 430 114 380 112 Q 330 114 320 144 Z" fill={TRAIT} />
      <rect x={312} y={108} width={30} height={8} rx={4} fill={O} transform="rotate(-30 327 112)" />
    </g>
  );
};

const Tenue: React.FC<{ qui: Personnage }> = ({ qui }) => {
  const corps = "M 318 232 Q 380 214 442 232 L 466 440 L 294 440 Z";
  if (qui === "commercante") return (
    <g>
      <path d={corps} fill={O} />
      {[290, 340, 390].map((y) => <path key={y} d={`M 306 ${y} L 330 ${y - 14} L 354 ${y} L 378 ${y - 14} L 402 ${y} L 426 ${y - 14} L 452 ${y}`}
        fill="none" stroke={B} strokeWidth={6} strokeLinejoin="round" />)}
    </g>
  );
  if (qui === "artisan") return (
    <g>
      <path d={corps} fill={G} />
      <path d="M 340 286 L 420 286 L 430 440 L 330 440 Z" fill={O} />
      <rect x={362} y={318} width={36} height={26} rx={4} fill="none" stroke={B} strokeWidth={4} />
      <line x1={340} y1={286} x2={330} y2={236} stroke={O} strokeWidth={6} />
      <line x1={420} y1={286} x2={430} y2={236} stroke={O} strokeWidth={6} />
    </g>
  );
  if (qui === "salarie") return (
    <g>
      <path d={corps} fill={G} />
      <path d="M 350 226 L 380 300 L 410 226 Z" fill={B} />
      <path d="M 372 238 L 388 238 L 394 310 L 380 330 L 366 310 Z" fill={O} />
      <path d="M 350 226 L 380 300 L 360 296 Z M 410 226 L 380 300 L 400 296 Z" fill="#3A3A42" />
    </g>
  );
  return (
    <g>
      <path d={corps} fill={B} />
      <path d="M 334 232 L 340 440 M 426 232 L 420 440" stroke={O} strokeWidth={14} strokeLinecap="round" />
      <circle cx={380} cy={300} r={18} fill={O} />
    </g>
  );
};

const Visage: React.FC<{ expression: Expression; regard: number }> = ({ expression, regard }) => {
  const f = useCurrentFrame();
  const cligne = f % 96 < 4 ? 0.12 : 1; // un clignement toutes les 3 s environ
  const sourcils: Record<Expression, [string, string]> = {
    contente: ["M 344 126 Q 356 118 368 125", "M 392 125 Q 404 118 416 126"],
    inquiete: ["M 344 132 L 368 122", "M 392 122 L 416 132"],
    surprise: ["M 344 118 Q 356 108 368 117", "M 392 117 Q 404 108 416 118"],
    pensive: ["M 344 124 Q 356 116 368 122", "M 392 128 L 416 128"],
  };
  const bouche: Record<Expression, React.ReactNode> = {
    contente: <path d="M 360 178 Q 380 200 400 178 Z" fill={TRAIT} />,
    inquiete: <path d="M 364 192 Q 380 178 396 192" fill="none" stroke={TRAIT} strokeWidth={5} strokeLinecap="round" />,
    surprise: <ellipse cx={380} cy={188} rx={9} ry={12} fill={TRAIT} />,
    pensive: <path d="M 368 188 L 394 183" fill="none" stroke={TRAIT} strokeWidth={5} strokeLinecap="round" />,
  };
  return (
    <g>
      {[356, 404].map((x) => (
        <g key={x} transform={`translate(${x} 150) scale(1 ${cligne})`}>
          <ellipse rx={11} ry={13} fill={B} />
          <circle cx={regard * 4} cy={1} r={6} fill={TRAIT} />
          <circle cx={regard * 4 + 2} cy={-2} r={2} fill={B} />
        </g>
      ))}
      {sourcils[expression].map((d, k) => <path key={k} d={d} fill="none" stroke={TRAIT} strokeWidth={5} strokeLinecap="round" />)}
      <path d="M 380 156 Q 372 170 383 171" fill="none" stroke={TRAIT} strokeOpacity={0.6} strokeWidth={3} strokeLinecap="round" />
      {bouche[expression]}
    </g>
  );
};

// petits signes autour de la tête : étincelles, goutte, « ! », bulle de pensée
const Signe: React.FC<{ expression: Expression; geste: Geste }> = ({ expression, geste }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: f - 14, fps, config: { damping: 12, stiffness: 160 } });
  if (expression === "pensive" || geste === "reflechit") {
    return (
      <g opacity={p}>
        {[[452, 112, 7], [474, 86, 11]].map(([x, y, r], k) => <circle key={k} cx={x} cy={y} r={r} fill={B} />)}
        <ellipse cx={540} cy={58} rx={52} ry={40} fill={B} />
        <text x={540} y={76} textAnchor="middle" fontFamily={fontFamily} fontWeight={900} fontSize={50} fill={O}>?</text>
      </g>
    );
  }
  if (expression === "inquiete") {
    const y = 96 + ((f % 40) / 40) * 30;
    return <path d={`M 452 ${y} C 444 ${y + 14} 444 ${y + 22} 452 ${y + 22} C 460 ${y + 22} 460 ${y + 14} 452 ${y} Z`} fill={B} opacity={p} />;
  }
  if (expression === "surprise") {
    return <text x={480} y={92} transform={`rotate(${Math.sin(f / 4) * 8} 480 70)`} fontFamily={fontFamily} fontWeight={900}
      fontSize={70} fill={O} opacity={p}>!</text>;
  }
  return (
    <g opacity={p}>
      {[[290, 92], [470, 80], [486, 150]].map(([x, y], k) => {
        const s = 0.6 + 0.4 * Math.abs(Math.sin(f / 8 + k));
        return <path key={k} d="M 0 -16 L 4 -4 L 16 0 L 4 4 L 0 16 L -4 4 L -16 0 L -4 -4 Z" fill={O}
          transform={`translate(${x} ${y}) scale(${s})`} />;
      })}
    </g>
  );
};

// objet tenu en main
const Objet: React.FC<{ geste: Geste; main: P; p: number }> = ({ geste, main, p }) => {
  if (geste === "tient_billet") return (
    <g opacity={p} transform={`translate(${main[0] - 6} ${main[1] - 46}) rotate(-8)`}>
      <rect width={110} height={52} rx={6} fill={B} stroke={O} strokeWidth={4} />
      <circle cx={55} cy={26} r={14} fill="none" stroke={O} strokeWidth={4} />
    </g>
  );
  if (geste === "tient_document") return (
    <g opacity={p} transform={`translate(${main[0] - 10} ${main[1] - 110}) rotate(6)`}>
      <rect width={92} height={120} rx={6} fill={B} />
      {[24, 46, 68, 90].map((y) => <rect key={y} x={14} y={y} width={y === 90 ? 40 : 64} height={8} rx={4} fill={GC} />)}
    </g>
  );
  return null;
};

export const PersonnageAnime: React.FC<{ qui?: Personnage; expression?: Expression; geste?: Geste; texte?: string; cx?: number }> = (
  { qui = "commercante", expression = "contente", geste = "repos", texte, cx = 380 }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const entree = spring({ frame: f, fps, config: { damping: 15, stiffness: 120, mass: 0.8 } });
  const p = spring({ frame: f - 8, fps, config: { damping: 13, stiffness: 110 } }); // le bras part au geste
  const souffle = Math.sin(f / 14) * 2.5;
  const peau = PEAU[qui], manche = HABIT[qui];
  let [coudeD, mainD] = BRAS_D[geste].map((pt, k) => mix(REPOS_D[k], pt, p)) as [P, P];
  if (geste === "salue") { const a = Math.sin(f / 4) * 14 * p; mainD = [mainD[0] + a, mainD[1] + Math.abs(a) / 3]; }
  const [coudeG, mainG] = (expression === "inquiete" ? JOUE_G : REPOS_G).map((pt, k) => mix(REPOS_G[k], pt, p)) as [P, P];
  const regard = geste === "montre" ? 1 : geste === "reflechit" ? -0.5 : 0;
  return (
    <g transform={`translate(${cx - 380} ${(1 - entree) * 80})`} opacity={entree}>
      <ellipse cx={380} cy={442} rx={110} ry={10} fill="#000000" opacity={0.35} />
      <g transform={`translate(0 ${souffle})`}>
        <Bras epaule={[318, 240]} coude={coudeG} main={mainG} manche={manche} peau={peau} />
        <Tenue qui={qui} />
        <rect x={366} y={198} width={28} height={34} fill={peau} />
        <circle cx={318} cy={156} r={12} fill={peau} />
        <circle cx={442} cy={156} r={12} fill={peau} />
        <circle cx={380} cy={150} r={62} fill={peau} />
        <Cheveux qui={qui} />
        <Visage expression={expression} regard={regard} />
        <Bras epaule={[442, 240]} coude={coudeD} main={mainD} manche={manche} peau={peau} />
        {geste === "montre" && <path d={`M ${mainD[0] + 10} ${mainD[1] - 4} l 30 -4`} stroke={peau} strokeWidth={10} strokeLinecap="round" />}
        <Objet geste={geste} main={mainD} p={p} />
      </g>
      <Signe expression={expression} geste={geste} />
      {texte && <g opacity={p}>
        <rect x={380 - (texte.length * 9 + 30)} y={452} width={(texte.length * 9 + 30) * 2} height={44} rx={22} fill={B} />
        <text x={380} y={483} textAnchor="middle" fontFamily={fontFamily} fontWeight={900} fontSize={26} fill={N}>{texte}</text>
      </g>}
    </g>
  );
};

// pour l'ancien type « personne » : devine le personnage d'après le mot affiché
export const deviner = (texte?: string): Personnage => {
  const t = (texte || "").toLowerCase();
  if (/étudi|élève|jeune|école/.test(t)) return "etudiante";
  if (/artisan|soud|ouvri|mécan|menuis|atelier|agricult|paysan/.test(t)) return "artisan";
  if (/salari|employ|fonction|cadre|agent|parent|père|ménage/.test(t)) return "salarie";
  return "commercante";
};
