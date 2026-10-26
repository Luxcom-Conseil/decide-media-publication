// Illustrations animées du gabarit V2 : dessins plats aux couleurs DECIDE (orange, noir, blanc), sans dégradé ni 3D.
// Chaque dessin occupe une zone 760×500 et s'anime à partir de la première image de sa scène.
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";

const { fontFamily } = loadFont("normal", { weights: ["700", "900"], subsets: ["latin", "latin-ext"] });
const O = "#F26A1B", B = "#FFFFFF", N = "#0E0E0E", G = "#3A3A40", GC = "#9A9AA2";

export type Illustration = { type: string; sens?: "baisse" | "hausse"; avant?: string; apres?: string; montant?: string; a?: string; b?: string; texte?: string };

// 0 → 1 avec un léger rebond, à partir de `delai` images
const useApparition = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (delai: number, raideur = 140) => spring({ frame: f - delai, fps, config: { damping: 14, stiffness: raideur, mass: 0.7 } });
};
const lin = (f: number, a: number, b: number, de = 0, a2 = 1) => interpolate(f, [a, b], [de, a2], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
const T: React.FC<React.SVGProps<SVGTextElement> & { t: string }> = ({ t, ...p }) =>
  <text fontFamily={fontFamily} fontWeight={900} textAnchor="middle" {...p}>{t}</text>;

const Piece: React.FC<{ x: number; y: number; r?: number }> = ({ x, y, r = 26 }) => (
  <g><circle cx={x} cy={y} r={r} fill={O} stroke={B} strokeWidth={4} /><T t="F" x={x} y={y + r * 0.38} fontSize={r} fill={B} /></g>
);
const Billet: React.FC<{ x: number; y: number; w?: number }> = ({ x, y, w = 150 }) => (
  <g><rect x={x} y={y} width={w} height={w * 0.45} rx={6} fill={B} stroke={O} strokeWidth={4} />
    <circle cx={x + w / 2} cy={y + w * 0.225} r={w * 0.13} fill="none" stroke={O} strokeWidth={4} /></g>
);

const Banque: React.FC = () => {
  const f = useCurrentFrame(), ap = useApparition();
  const fronton = ap(14);
  return (
    <g>
      <rect x={150} y={420} width={460} height={22} fill={B} transform={`scale(${ap(0)} 1)`} style={{ transformOrigin: "380px 430px" }} />
      <rect x={180} y={398} width={400} height={22} fill={B} opacity={ap(3)} />
      {[0, 1, 2, 3, 4].map((k) => (
        <rect key={k} x={205 + k * 80} y={220} width={36} height={178} fill={B} style={{ transformOrigin: `${223 + k * 80}px 398px` }}
          transform={`scale(1 ${ap(5 + k * 2)})`} />
      ))}
      <g transform={`translate(0 ${(1 - fronton) * -120})`} opacity={fronton}>
        <rect x={180} y={180} width={400} height={40} fill={B} />
        <polygon points="160,180 380,80 600,180" fill={O} />
        <T t="BANQUE" x={380} y={210} fontSize={30} fill={N} />
      </g>
      {[0, 1, 2].map((k) => {
        const t = ((f - 30 - k * 12) % 45) / 45;
        return f > 30 + k * 12 ? <g key={k} opacity={1 - t}><Piece x={380 + t * 300} y={360 - Math.sin(t * Math.PI) * 120} r={22} /></g> : null;
      })}
    </g>
  );
};

const Rembourser: React.FC = () => {
  const ap = useApparition();
  const h1 = 220 * ap(4), h2 = 220 * ap(16), extra = 70 * ap(30);
  return (
    <g>
      <rect x={140} y={420 - h1} width={170} height={h1} fill={B} rx={8} />
      <T t="PRÊTÉ" x={225} y={470} fontSize={34} fill={B} />
      <path d="M 340 300 L 420 300" stroke={GC} strokeWidth={8} markerEnd="url(#fl)" opacity={ap(10)} />
      <rect x={450} y={420 - h2} width={170} height={h2} fill={B} rx={8} />
      <rect x={450} y={420 - h2 - extra} width={170} height={extra} fill={O} rx={8} />
      <T t="RENDU" x={535} y={470} fontSize={34} fill={B} />
      <g opacity={ap(36)}><T t="+ le prix" x={535} y={410 - h2 - extra} fontSize={34} fill={O} /></g>
    </g>
  );
};

const Pays: React.FC = () => {
  const ap = useApparition();
  return (
    <g>
      <circle cx={380} cy={260} r={110 * ap(0)} fill={O} />
      <T t="CEMAC" x={380} y={274} fontSize={44} fill={B} opacity={ap(6)} />
      {[0, 1, 2, 3, 4, 5].map((k) => {
        const a = (k / 6) * Math.PI * 2 - Math.PI / 2, p = ap(10 + k * 4, 200);
        const x = 380 + Math.cos(a) * 200, y = 260 + Math.sin(a) * 180;
        return (
          <g key={k} transform={`translate(${x} ${y}) scale(${p})`}>
            <path d="M 0 -46 C -30 -46 -34 -10 0 26 C 34 -10 30 -46 0 -46 Z" fill={B} />
            <circle cx={0} cy={-22} r={11} fill={O} />
          </g>
        );
      })}
    </g>
  );
};

const Pourcent: React.FC<{ il: Illustration }> = ({ il }) => {
  const f = useCurrentFrame(), ap = useApparition();
  const baisse = il.sens !== "hausse";
  const p = lin(f, 18, 50);
  const y = baisse ? 150 + p * 200 : 350 - p * 200;
  return (
    <g>
      <line x1={110} y1={440} x2={650} y2={440} stroke={G} strokeWidth={6} />
      <rect x={150} y={baisse ? 150 : 350} width={150} height={baisse ? 290 : 90} fill={GC} rx={6} opacity={ap(0)} />
      <T t={il.avant ?? ""} x={225} y={baisse ? 130 : 330} fontSize={40} fill={GC} opacity={ap(4)} />
      <rect x={460} y={y} width={150} height={440 - y} fill={O} rx={6} opacity={ap(12)} />
      <T t={il.apres ?? ""} x={535} y={y - 20} fontSize={46} fill={O} opacity={ap(20)} />
      <g transform={`translate(380 ${baisse ? 200 + p * 60 : 300 - p * 60}) rotate(${baisse ? 35 : -35})`} opacity={ap(14)}>
        <rect x={-50} y={-12} width={80} height={24} fill={B} />
        <polygon points="30,-34 70,0 30,34" fill={B} />
      </g>
    </g>
  );
};

const Couturiere: React.FC = () => {
  const f = useCurrentFrame(), ap = useApparition();
  const aiguille = Math.abs(Math.sin(f / 3)) * 16;
  return (
    <g>
      {/* personne */}
      <g transform={`translate(0 ${(1 - ap(0)) * 60})`} opacity={ap(0)}>
        <path d="M 150 440 C 150 330 200 290 250 290 C 300 290 350 330 350 440 Z" fill={O} />
        <circle cx={250} cy={225} r={52} fill="#8A5A3C" />
        <path d="M 196 214 C 196 150 304 150 304 214 C 290 186 210 186 196 214 Z" fill={O} />
        <circle cx={250} cy={152} r={20} fill={O} />
      </g>
      {/* machine à coudre */}
      <g transform={`translate(${(1 - ap(10)) * 200} 0)`} opacity={ap(10)}>
        <rect x={360} y={400} width={300} height={40} rx={6} fill={B} />
        <path d="M 400 400 L 400 260 Q 400 230 430 230 L 620 230 Q 640 230 640 250 L 640 300 L 600 300 L 600 270 L 440 270 L 440 400 Z" fill={B} />
        <rect x={596} y={300 + aiguille} width={8} height={50} fill={O} />
        <circle cx={430} cy={300} r={18} fill={O} />
        <rect x={480} y={380} width={160} height={20} fill={GC} />
      </g>
      <T t="Exemple inventé" x={380} y={490} fontSize={26} fill={GC} opacity={ap(20)} />
    </g>
  );
};

// personne ordinaire (commerçant, parent, salarié…), avec un mot qui dit qui c'est
const Personne: React.FC<{ il: Illustration }> = ({ il }) => {
  const f = useCurrentFrame(), ap = useApparition();
  const p = ap(0);
  const salut = Math.sin(f / 5) * 8;
  return (
    <g>
      <g transform={`translate(0 ${(1 - p) * 60})`} opacity={p}>
        <path d="M 270 440 C 270 320 320 280 380 280 C 440 280 490 320 490 440 Z" fill={O} />
        <circle cx={380} cy={210} r={58} fill="#8A5A3C" />
        <path d={`M 470 330 L 540 ${250 + salut} L 560 ${262 + salut} L 490 345 Z`} fill={O} />
        <circle cx={552} cy={250 + salut} r={18} fill="#8A5A3C" />
      </g>
      {il.texte && <g opacity={ap(10)}><rect x={230} y={455} width={300} height={44} rx={22} fill={B} />
        <T t={il.texte} x={380} y={487} fontSize={28} fill={N} /></g>}
    </g>
  );
};

const Contrat: React.FC<{ x: number; lettre: string; p: number; dx: number }> = ({ x, lettre, p, dx }) => (
  <g transform={`translate(${(1 - p) * dx} 0) rotate(${(1 - p) * (dx > 0 ? 10 : -10)} ${x + 110} 270)`} opacity={p}>
    <rect x={x} y={110} width={220} height={300} rx={10} fill={B} />
    {[0, 1, 2, 3].map((k) => <rect key={k} x={x + 30} y={230 + k * 34} width={k === 3 ? 90 : 160} height={12} fill={GC} rx={6} />)}
    <circle cx={x + 110} cy={170} r={42} fill={O} />
    <T t={lettre} x={x + 110} y={188} fontSize={52} fill={B} />
  </g>
);
const Contrats: React.FC = () => {
  const ap = useApparition();
  return (
    <g>
      <Contrat x={110} lettre="A" p={ap(2)} dx={-300} />
      <Contrat x={430} lettre="B" p={ap(10)} dx={300} />
      <T t="?" x={380} y={300} fontSize={110} fill={O} opacity={ap(20)} />
    </g>
  );
};

const Calendrier: React.FC<{ il: Illustration }> = ({ il }) => {
  const f = useCurrentFrame(), ap = useApparition();
  const mois = Math.max(1, Math.min(12, Math.floor(lin(f, 10, 100, 1, 12.99))));
  return (
    <g>
      <g transform={`scale(${ap(0)})`} style={{ transformOrigin: "220px 270px" }}>
        <rect x={90} y={110} width={260} height={290} rx={14} fill={B} />
        <rect x={90} y={110} width={260} height={70} rx={14} fill={O} />
        <rect x={90} y={160} width={260} height={20} fill={O} />
        <T t="MOIS" x={220} y={158} fontSize={34} fill={B} />
        <T t={String(mois)} x={220} y={330} fontSize={130} fill={N} />
      </g>
      {/* une pièce tombe chaque mois dans la pile */}
      {Array.from({ length: mois }).map((_, k) => <Piece key={k} x={540} y={430 - k * 18} r={30} />)}
      <T t={`${il.montant ?? ""} / mois`} x={540} y={130} fontSize={36} fill={B} opacity={ap(6)} />
    </g>
  );
};

const Pile: React.FC<{ il: Illustration }> = ({ il }) => {
  const f = useCurrentFrame(), ap = useApparition();
  const n = Math.floor(lin(f, 0, 40, 0, 12));
  return (
    <g>
      {Array.from({ length: n }).map((_, k) => <Billet key={k} x={230 + (k % 2) * 8} y={400 - k * 24} w={300} />)}
      <g opacity={ap(42)}><rect x={150} y={60} width={460} height={70} rx={35} fill={O} />
        <T t={`${il.montant ?? ""} FCFA`} x={380} y={110} fontSize={44} fill={B} /></g>
    </g>
  );
};

const Frais: React.FC<{ il: Illustration }> = ({ il }) => {
  const f = useCurrentFrame(), ap = useApparition();
  const p = ap(4, 120);
  const secousse = f > 20 && f < 34 ? Math.sin(f * 2.2) * 6 : 0;
  return (
    <g transform={`translate(${secousse} ${(1 - p) * -260})`} opacity={p}>
      <path d="M 230 90 L 530 90 L 530 420 L 505 400 L 480 420 L 455 400 L 430 420 L 405 400 L 380 420 L 355 400 L 330 420 L 305 400 L 280 420 L 255 400 L 230 420 Z" fill={B} />
      <T t="FRAIS" x={380} y={170} fontSize={56} fill={N} />
      <rect x={270} y={200} width={220} height={10} fill={GC} />
      <T t={il.montant ?? ""} x={380} y={300} fontSize={64} fill={O} />
      <T t="FCFA" x={380} y={355} fontSize={36} fill={N} />
    </g>
  );
};

const Balance: React.FC<{ il: Illustration }> = ({ il }) => {
  const f = useCurrentFrame(), ap = useApparition();
  const angle = interpolate(f, [12, 40], [0, 9], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }); // B plus lourd
  const rad = (angle * Math.PI) / 180;
  const ya = 170 - Math.sin(rad) * 230, yb = 170 + Math.sin(rad) * 230;
  const Plateau: React.FC<{ x: number; y: number; l: string; m: string; c: string }> = ({ x, y, l, m, c }) => (
    <g>
      <line x1={x} y1={y} x2={x - 70} y2={y + 120} stroke={B} strokeWidth={4} />
      <line x1={x} y1={y} x2={x + 70} y2={y + 120} stroke={B} strokeWidth={4} />
      <path d={`M ${x - 90} ${y + 120} L ${x + 90} ${y + 120} Q ${x} ${y + 175} ${x - 90} ${y + 120} Z`} fill={c} />
      <T t={l} x={x} y={y + 105} fontSize={50} fill={c} />
      <T t={m} x={x} y={y + 215} fontSize={34} fill={B} />
    </g>
  );
  return (
    <g opacity={ap(0)}>
      <polygon points="350,440 410,440 380,180" fill={GC} />
      <g transform={`rotate(${angle} 380 170)`}><rect x={150} y={162} width={460} height={16} rx={8} fill={B} /></g>
      <circle cx={380} cy={170} r={16} fill={O} />
      <Plateau x={380 - Math.cos(rad) * 230} y={ya} l="A" m={il.a ?? ""} c={B} />
      <Plateau x={380 + Math.cos(rad) * 230} y={yb} l="B" m={il.b ?? ""} c={O} />
    </g>
  );
};

const Loupe: React.FC = () => {
  const f = useCurrentFrame(), ap = useApparition();
  const y = interpolate(f, [8, 40], [170, 330], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const total = f > 40;
  return (
    <g opacity={ap(0)}>
      <rect x={210} y={70} width={340} height={380} rx={12} fill={B} />
      {[0, 1, 2, 3].map((k) => <rect key={k} x={250} y={120 + k * 50} width={260} height={14} rx={7} fill={GC} />)}
      <rect x={240} y={315} width={280} height={56} rx={8} fill={total ? O : "#DDDDE2"} />
      <T t="TOTAL" x={380} y={355} fontSize={38} fill={total ? B : GC} />
      <g transform={`translate(${470} ${y})`}>
        <circle cx={0} cy={0} r={70} fill="none" stroke={N} strokeWidth={16} />
        <circle cx={0} cy={0} r={70} fill="none" stroke={O} strokeWidth={8} />
        <rect x={48} y={44} width={90} height={26} rx={12} fill={N} transform="rotate(45 48 44)" />
      </g>
    </g>
  );
};

const Liste: React.FC = () => {
  const f = useCurrentFrame(), ap = useApparition();
  const lignes = ["Chaque paiement", "Tous les frais", "Le total"];
  return (
    <g opacity={ap(0)}>
      <rect x={150} y={60} width={460} height={400} rx={14} fill={B} />
      <rect x={150} y={60} width={460} height={70} rx={14} fill={O} />
      <rect x={150} y={110} width={460} height={20} fill={O} />
      <T t="TABLEAU DES PAIEMENTS" x={380} y={108} fontSize={28} fill={B} />
      {lignes.map((l, k) => {
        const p = lin(f, 12 + k * 14, 22 + k * 14);
        return (
          <g key={k}>
            <rect x={190} y={170 + k * 90} width={52} height={52} rx={8} fill="none" stroke={N} strokeWidth={5} />
            <path d={`M 198 ${196 + k * 90} L 212 ${210 + k * 90} L 236 ${180 + k * 90}`} fill="none" stroke={O} strokeWidth={9}
              strokeLinecap="round" strokeDasharray={60} strokeDashoffset={60 * (1 - p)} />
            <text x={262} y={208 + k * 90} fontFamily={fontFamily} fontWeight={700} fontSize={32} fill={N}>{l}</text>
          </g>
        );
      })}
    </g>
  );
};

export const Dessin: React.FC<{ il: Illustration }> = ({ il }) => (
  <svg viewBox="0 0 760 500" width={760} height={500} style={{ overflow: "visible" }}>
    <defs>
      <marker id="fl" markerWidth={4} markerHeight={4} refX={2} refY={2} orient="auto"><path d="M0,0 L4,2 L0,4 Z" fill={GC} /></marker>
    </defs>
    {il.type === "banque" && <Banque />}
    {il.type === "rembourser" && <Rembourser />}
    {il.type === "pays" && <Pays />}
    {il.type === "pourcent" && <Pourcent il={il} />}
    {il.type === "couturiere" && <Couturiere />}
    {il.type === "personne" && <Personne il={il} />}
    {il.type === "contrats" && <Contrats />}
    {il.type === "calendrier" && <Calendrier il={il} />}
    {il.type === "pile" && <Pile il={il} />}
    {il.type === "frais" && <Frais il={il} />}
    {il.type === "balance" && <Balance il={il} />}
    {il.type === "loupe" && <Loupe />}
    {il.type === "liste" && <Liste />}
  </svg>
);
