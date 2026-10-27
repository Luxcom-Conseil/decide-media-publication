// Carte animée : l'Afrique en aplat, la caméra zoome sur la région des lieux cités, puis un repère tombe sur chaque
// lieu (rebond + onde) avec son nom. texte = « Yaoundé | Douala » ; lieux connus : lieux.json (villes et pays).
// Dessin dans la zone 760×500 des illustrations.
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";
import LIEUX from "./lieux.json";

const { fontFamily } = loadFont("normal", { weights: ["800"], subsets: ["latin", "latin-ext"] });
const O = "#F26A1B", B = "#FFFFFF", SOL = "#3A3A42", BORD = "#6A6A74", MER = "#0F2233";

// contour simplifié du continent (longitude, latitude)
const AFRIQUE: [number, number][] = [[-5.8, 35.8], [10, 37.2], [11.5, 33], [19, 30.5], [25, 31.6], [32.3, 31.3], [32.5, 29.9], [35, 24],
  [37.3, 19], [39.5, 15.5], [43.3, 12.5], [51.2, 11.8], [49, 6], [42, -1], [40, -5], [39.3, -10], [40.5, -15], [35, -20], [35.5, -24],
  [32.6, -26], [30, -31], [25.6, -34], [20, -34.8], [18.4, -34], [17, -29], [15, -26.5], [14.5, -22.5], [11.8, -17.2], [13.5, -11],
  [12.2, -6], [9.4, -0.5], [9, 1], [9.5, 4], [8.5, 4.5], [6, 4.3], [3, 6.4], [-1, 5], [-4, 5.2], [-7.5, 4.4], [-11.5, 7], [-13.3, 9],
  [-15.5, 11.5], [-17.5, 14.7], [-16.5, 19.5], [-17, 21], [-15, 25], [-13, 27.7], [-9.8, 30], [-9.3, 32.5], [-6.8, 34]];

const cle = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[’']/g, "'").trim();
export const lieuConnu = (nom: string) => (LIEUX as unknown as Record<string, [number, number]>)[cle(nom)];

// projection simple : 1° = 1 unité, latitude inversée
const P = ([lon, lat]: [number, number]) => [lon, -lat] as const;

export const Carte: React.FC<{ texte?: string }> = ({ texte }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const lieux = (texte ?? "").split("|").map((n) => n.trim()).filter(Boolean)
    .map((nom) => ({ nom, pos: lieuConnu(nom) })).filter((l): l is { nom: string; pos: [number, number] } => !!l.pos).slice(0, 4);
  // vue de départ : tout le continent ; vue d'arrivée : les lieux, avec une marge, zoom au plus ×6
  const tout = { x: 17, y: -1, l: 115 };
  let fin = tout;
  if (lieux.length) {
    const xs = lieux.map((l) => P(l.pos)[0]), ys = lieux.map((l) => P(l.pos)[1]);
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    // 34° de large au plus près : la côte et les pays voisins restent visibles (à 12°, on ne reconnaissait plus rien)
    const l = Math.min(115, Math.max(34,(Math.max(...xs) - Math.min(...xs)) * 1.8, (Math.max(...ys) - Math.min(...ys)) * 2.6));
    fin = { x: cx, y: cy, l };
  }
  const z = spring({ frame: f - 6, fps, config: { damping: 20, stiffness: 60 } });
  const vue = { x: interpolate(z, [0, 1], [tout.x, fin.x]), y: interpolate(z, [0, 1], [tout.y, fin.y]), l: interpolate(z, [0, 1], [tout.l, fin.l]) };
  const echelle = 760 / vue.l; // pixels par degré : les repères gardent la même taille à l'écran
  const t = (lon: number, lat: number) => { const [x, y] = P([lon, lat]); return [(x - vue.x) * echelle + 380, (y - vue.y) * echelle + 250] as const; };
  const contour = AFRIQUE.map(([lon, lat], k) => { const [x, y] = t(lon, lat); return `${k ? "L" : "M"}${x},${y}`; }).join(" ") + " Z";
  const [mx, my] = t(46.6, -19.5);
  // un lieu proche du précédent a son nom de l'autre côté du repère : les étiquettes ne se chevauchent plus
  const dessus: boolean[] = [];
  lieux.forEach((l, k) => {
    const [x, y] = t(...l.pos), prec = k ? t(...lieux[k - 1].pos) : null;
    dessus.push(!!prec && Math.abs(prec[0] - x) < 170 && Math.abs(prec[1] - y) < 100 ? !dessus[k - 1] : false);
  });
  return (
    <g>
      <defs><clipPath id="cadre-carte"><rect x={0} y={0} width={760} height={500} rx={24} /></clipPath></defs>
      <g clipPath="url(#cadre-carte)">
        <rect x={0} y={0} width={760} height={500} fill={MER} />
        <path d={contour} fill={SOL} stroke={BORD} strokeWidth={3} strokeLinejoin="round" />
        <ellipse cx={mx} cy={my} rx={2.4 * echelle} ry={6.5 * echelle} fill={SOL} stroke={BORD} strokeWidth={3} transform={`rotate(20 ${mx} ${my})`} />
        {lieux.map((l, k) => {
          const [x, y] = t(...l.pos);
          const d = 30 + k * 10;
          const chute = spring({ frame: f - d, fps, config: { damping: 9, stiffness: 160, mass: 0.6 } });
          const onde = ((f - d - 8) % 40) / 40;
          const ly = dessus[k] ? y - 110 : y + 14;
          return (
            <g key={k} opacity={Math.min(1, chute * 2)}>
              {f > d + 8 && <circle cx={x} cy={y} r={10 + onde * 50} fill="none" stroke={O} strokeWidth={4} opacity={1 - onde} />}
              <ellipse cx={x} cy={y} rx={14} ry={5} fill="#000" opacity={0.4 * chute} />
              <g transform={`translate(${x} ${y - (1 - chute) * 160})`}>
                <path d="M0,0 C-8,-14 -24,-26 -24,-44 A24,24 0 1 1 24,-44 C24,-26 8,-14 0,0 Z" fill={O} stroke={B} strokeWidth={4} />
                <circle cx={0} cy={-44} r={9} fill={B} />
              </g>
              <g opacity={interpolate(f, [d + 10, d + 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}>
                <rect x={x - (l.nom.length * 14 + 24) / 2} y={ly} width={l.nom.length * 14 + 24} height={40} rx={8} fill={B} />
                <text x={x} y={ly + 28} textAnchor="middle" fontFamily={fontFamily} fontWeight={800} fontSize={24} fill="#0E0E0E">{l.nom}</text>
              </g>
            </g>
          );
        })}
      </g>
    </g>
  );
};
