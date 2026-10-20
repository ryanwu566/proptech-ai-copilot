import type { CSSProperties, ReactNode } from "react";
import type { AmbientVariant } from "@/lib/ambient/scene-model";
import s from "./ambient-scene.module.css";

/**
 * Scene geometry only: semantic shapes, never values, labels or case data. Timing, opacity and pausing belong to
 * AmbientScene. Desktop artboards are 1600×880 (anchored top-right), mobile artboards 390×560 with one idea each.
 */
type Artboard = { viewBox: string; align?: string; layers: ReactNode };
export type SceneGeometry = { desktop: Artboard; mobile: Artboard };

const cx = (...names: (string | false | undefined)[]) => names.filter(Boolean).join(" ");
/** Per-element motion parameters: settle offset, target opacity, resting opacity and stagger. */
const m = ({ dx, dy, o, rest, delay }: { dx?: number; dy?: number; o?: number; rest?: number; delay?: number }) => ({
  ...(dx !== undefined && { "--dx": `${dx}px` }),
  ...(dy !== undefined && { "--dy": `${dy}px` }),
  ...(o !== undefined && { "--o": o }),
  ...(rest !== undefined && { "--rest": rest }),
  ...(delay !== undefined && { transitionDelay: `${delay}ms` }),
}) as CSSProperties;

/** Deterministic pseudo-random numbers so server and client render identical geometry. */
function seeded(seed: number) {
  let t = seed >>> 0;
  return () => {
    t = (t + 0x6d2b79f5) >>> 0;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}
const round = (value: number) => Math.round(value * 10) / 10;
/** Many dots as one compound path keeps each cluster a single DOM node. */
const dots = (points: [number, number][], r: number) => points.map(([x, y]) => `M${round(x - r)} ${round(y)}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0`).join("");
const lines = (segments: [number, number, number, number][]) => segments.map(([x1, y1, x2, y2]) => `M${x1} ${y1}L${x2} ${y2}`).join("");
const rects = (boxes: [number, number, number, number][]) => boxes.map(([x, y, w, h]) => `M${x} ${y}h${w}v${h}h${-w}z`).join("");
/** A smooth closed contour (closed Catmull-Rom spline through a wobbled ellipse). */
function contour(cx0: number, cy0: number, rx: number, ry: number, seed: number, wobble = 0.12, count = 9) {
  const random = seeded(seed);
  const points = Array.from({ length: count }, (_, index) => {
    const angle = (index / count) * Math.PI * 2;
    const scale = 1 + (random() * 2 - 1) * wobble;
    return [cx0 + Math.cos(angle) * rx * scale, cy0 + Math.sin(angle) * ry * scale] as const;
  });
  let d = `M${round(points[0][0])} ${round(points[0][1])}`;
  for (let index = 0; index < count; index++) {
    const [p0, p1, p2, p3] = [-1, 0, 1, 2].map((offset) => points[(index + offset + count) % count]);
    d += `C${round(p1[0] + (p2[0] - p0[0]) / 6)} ${round(p1[1] + (p2[1] - p0[1]) / 6)} ${round(p2[0] - (p3[0] - p1[0]) / 6)} ${round(p2[1] - (p3[1] - p1[1]) / 6)} ${round(p2[0])} ${round(p2[1])}`;
  }
  return `${d}Z`;
}
function scatter(seed: number, count: number, x: [number, number], y: [number, number]) {
  const random = seeded(seed);
  // Two uniforms averaged give a soft central tendency without looking like a plotted distribution.
  return Array.from({ length: count }, () => [x[0] + random() * (x[1] - x[0]), y[0] + ((random() + random()) / 2) * (y[1] - y[0])] as [number, number]);
}

const DESKTOP = "0 0 1600 880";
const MOBILE = "0 0 390 560";

/* MARKET — transactions settle into a P25–median–P75 band; one asking-price marker locks inside it. */
const market: SceneGeometry = {
  desktop: { viewBox: DESKTOP, layers: <>
    <path className={cx(s.ink, s.faint)} d={lines([200, 280, 440, 520].map((y) => [760, y, 1600, y]))} />
    <rect className={cx(s.band, s.fadeFocus)} x={760} y={300} width={840} height={120} />
    <path className={cx(s.ink, s.draw, s.recede)} style={m({ rest: 0.5 })} pathLength={1} d="M760 300H1600M760 420H1600" />
    <path className={cx(s.accent, s.drawLock)} pathLength={1} d="M760 360H1600" />
    {[[11, -46, 0.8], [23, 42, 0.62], [37, -24, 0.5]].map(([seed, dy, o], index) =>
      <path key={seed} className={cx(s.dot, s.fadeFocus, s.settle)} style={m({ dy, o, delay: index * 160 })} d={dots(scatter(seed, 16, [790, 1580], [270, 450]), 2.2)} />)}
    <g className={s.lockMark}>
      <path className={s.accent} d="M1290 272V448" />
      <path className={s.solid} d="M1290 330l8 8-8 8-8-8z" />
    </g>
    <path className={cx(s.accent, s.trace, s.w0)} pathLength={1} d="M760 360H1600" />
    <circle className={cx(s.accent, s.halo, s.w1)} cx={1290} cy={338} r={16} />
  </> },
  mobile: { viewBox: MOBILE, layers: <>
    <rect className={cx(s.band, s.fadeFocus)} x={0} y={150} width={390} height={86} />
    <path className={cx(s.accent, s.drawLock)} pathLength={1} d="M0 193H390" />
    <g className={s.lockMark}><path className={s.accent} d="M282 164V222" /><path className={s.node} d="M282 180l7 7-7 7-7-7z" /></g>
    <path className={cx(s.accent, s.trace, s.w0)} pathLength={1} d="M0 193H390" />
    <circle className={cx(s.accent, s.halo, s.w1)} cx={282} cy={187} r={14} />
  </> },
};

/* LOCATION — a quiet street grid with footprints; routes from the property to facilities wake one at a time. */
const STREET_X = [820, 930, 1060, 1160, 1290, 1400, 1520];
const STREET_Y = [110, 220, 330, 450, 560, 670];
function footprints(seed: number, xs: number[], ys: number[]) {
  const random = seeded(seed);
  const boxes: [number, number, number, number][] = [];
  for (let i = 0; i < xs.length - 1; i++) for (let j = 0; j < ys.length - 1; j++) {
    const [x0, x1, y0, y1] = [xs[i] + 12, xs[i + 1] - 12, ys[j] + 12, ys[j + 1] - 12];
    const split = x0 + (x1 - x0) * (0.4 + random() * 0.2);
    boxes.push([x0, y0, round(split - x0 - 6), round((y1 - y0) * (0.55 + random() * 0.4))]);
    boxes.push([round(split + 6), round(y0 + random() * 10), round(x1 - split - 6), round((y1 - y0) * (0.45 + random() * 0.45))]);
  }
  return rects(boxes);
}
const ROUTES = ["M1225 270H1160V220H930", "M1225 270H1290V450H1520", "M1225 270V560H1060"];
const location: SceneGeometry = {
  desktop: { viewBox: DESKTOP, layers: <g transform="rotate(-6 1200 400)">
    <path className={cx(s.band, s.faint)} d={footprints(7, STREET_X, STREET_Y)} />
    <path className={cx(s.ink, s.faint)} d={lines([...STREET_X.map((x) => [x, 40, x, 760] as [number, number, number, number]), ...STREET_Y.map((y) => [740, y, 1640, y] as [number, number, number, number])])} />
    <path className={s.ink} strokeWidth={2.5} opacity={0.35} d="M740 330H1640" />
    <path className={cx(s.node, s.fadeFocus)} d={dots([[930, 220], [1520, 450], [1060, 560], [1400, 110], [820, 450]], 5)} />
    {ROUTES.map((d, index) => <path key={d} className={cx(s.accent, s.drawLock, s.recede)} style={m({ rest: 0.45, delay: index * 220 })} pathLength={1} d={d} />)}
    <g className={s.lockMark}><rect className={s.accent} x={1214} y={261} width={22} height={18} rx={2} /><circle className={s.accent} cx={1225} cy={270} r={22} opacity={0.5} /></g>
    {ROUTES.map((d, index) => <path key={d} className={cx(s.accent, s.trace, [s.w0, s.w1, s.w2][index])} strokeWidth={2} pathLength={1} d={d} />)}
  </g> },
  mobile: { viewBox: MOBILE, layers: <g transform="rotate(-6 200 260)">
    <path className={cx(s.band, s.faint)} d={footprints(3, [40, 150, 270, 380], [60, 180, 300, 420])} />
    <path className={cx(s.ink, s.faint)} d={lines([...[40, 150, 270, 380].map((x) => [x, 0, x, 520] as [number, number, number, number]), ...[60, 180, 300, 420].map((y) => [-20, y, 420, y] as [number, number, number, number])])} />
    <path className={cx(s.node, s.fadeFocus)} d={dots([[150, 60], [380, 300]], 5)} />
    <path className={cx(s.accent, s.drawLock, s.recede)} style={m({ rest: 0.45 })} pathLength={1} d="M260 240H150V60M260 240H270V300H380" />
    <g className={s.lockMark}><rect className={s.node} x={250} y={232} width={20} height={16} rx={2} /></g>
    <path className={cx(s.accent, s.trace, s.w0)} strokeWidth={2} pathLength={1} d="M260 240H150V60" />
    <path className={cx(s.accent, s.trace, s.w1)} strokeWidth={2} pathLength={1} d="M260 240H270V300H380" />
  </g> },
};

/* RISK — faint hazard contours and one polygon; a single amber dashed zone stays visibly unresolved, never safe-looking. */
const RISK_CONTOURS = [[230, 150, 3], [178, 116, 5], [126, 82, 8], [76, 50, 13]] as const;
const AMBER = contour(1430, 210, 92, 58, 21, 0.1, 8);
const risk: SceneGeometry = {
  desktop: { viewBox: DESKTOP, layers: <>
    {RISK_CONTOURS.map(([rx, ry, seed], index) => <path key={seed} className={cx(s.ink, s.draw, s.recede)} style={m({ rest: 0.6 - index * 0.08, delay: index * 180 })} pathLength={1} d={contour(1210, 380, rx, ry, seed)} />)}
    <path className={cx(s.ink, s.faint, s.fadeFocus)} strokeDasharray="2 6" d="M880 520L1010 470 1100 540 1060 640 920 650Z" />
    <path className={cx(s.amber, s.lockMark)} d={AMBER} />
    <rect className={cx(s.ink, s.fadeLock)} x={1200} y={372} width={18} height={16} rx={2} />
    <path className={cx(s.ink, s.trace, s.w0)} strokeWidth={1.5} pathLength={1} d={contour(1210, 380, 230, 150, 3)} />
    <path className={cx(s.amberLine, s.trace, s.w1)} pathLength={1} d={AMBER} />
  </> },
  mobile: { viewBox: MOBILE, layers: <>
    {[[150, 100, 3], [96, 64, 8]].map(([rx, ry, seed], index) => <path key={seed} className={cx(s.ink, s.draw, s.recede)} style={m({ rest: 0.55, delay: index * 180 })} pathLength={1} d={contour(190, 260, rx, ry, seed)} />)}
    <path className={cx(s.amber, s.lockMark)} d={contour(318, 120, 62, 40, 21, 0.1, 8)} />
    <path className={cx(s.amberLine, s.trace, s.w1)} pathLength={1} d={contour(318, 120, 62, 40, 21, 0.1, 8)} />
    <path className={cx(s.ink, s.trace, s.w0)} strokeWidth={1.5} pathLength={1} d={contour(190, 260, 150, 100, 3)} />
  </> },
};

/* FINANCE — equal payment steps accumulate along a timeline and settle. A staircase, not a market chart; neutral palette only. */
const steps = (x: number, y: number, count: number, width: number, rise: number) => `M${x} ${y}${Array.from({ length: count }, () => `h${width}v${-rise}`).join("")}`;
const STAIRS = steps(800, 446, 24, 32, 4);
const STAIRS_MOBILE = steps(0, 286, 12, 33, 5);
const finance: SceneGeometry = {
  desktop: { viewBox: DESKTOP, layers: <>
    <path className={s.ink} opacity={0.6} d="M780 470H1600" />
    <path className={cx(s.ink, s.fadeFocus)} style={m({ o: 0.7 })} d={lines(Array.from({ length: 25 }, (_, index) => [800 + index * 32, 470, 800 + index * 32, index % 12 === 0 ? 452 : 462]))} />
    <path className={cx(s.band, s.fadeLock)} d={rects(Array.from({ length: 24 }, (_, index) => [808 + index * 32, 480, 16, 10]))} />
    <path className={cx(s.band, s.fadeLock, s.settle)} style={m({ dy: 14 })} d={`${STAIRS}V470H800Z`} />
    <path className={cx(s.accent, s.draw)} pathLength={1} d={STAIRS} />
    <circle className={cx(s.node, s.lockMark)} cx={1568} cy={350} r={6} />
    <path className={cx(s.accent, s.trace, s.w0)} strokeWidth={2} pathLength={1} d={STAIRS} />
    <path className={cx(s.ink, s.trace, s.w1)} strokeWidth={2} pathLength={1} d="M800 470H1600" />
  </> },
  mobile: { viewBox: MOBILE, layers: <>
    <path className={s.ink} opacity={0.6} d="M0 300H390" />
    <path className={cx(s.ink, s.fadeFocus)} style={m({ o: 0.7 })} d={lines(Array.from({ length: 12 }, (_, index) => [16 + index * 33, 300, 16 + index * 33, 292]))} />
    <path className={cx(s.band, s.fadeLock, s.settle)} style={m({ dy: 12 })} d={`${STAIRS_MOBILE}V300H0Z`} />
    <path className={cx(s.accent, s.draw)} pathLength={1} d={STAIRS_MOBILE} />
    <path className={cx(s.accent, s.trace, s.w0)} strokeWidth={2} pathLength={1} d={STAIRS_MOBILE} />
  </> },
};

/* OVERVIEW — one property; price/market, location, risk and money converge toward it. */
const THEMES = [
  { at: [980, 170], dx: -50, dy: -36, glyph: <path className={s.ink} d="M-24 -10H24M-24 0H24M-24 10H24" />, link: "M1004 186C1080 230 1110 270 1136 300" },
  { at: [1430, 150], dx: 50, dy: -36, glyph: <><path className={s.ink} d="M-22 12H0V-12H22" /><circle className={s.node} cx={22} cy={-12} r={4} /></>, link: "M1408 168C1340 220 1300 260 1262 298" },
  { at: [1440, 520], dx: 50, dy: 36, glyph: <path className={s.ink} d={`${contour(0, 0, 26, 16, 4)}${contour(0, 0, 14, 8, 9)}`} />, link: "M1412 506C1340 450 1300 410 1262 364" },
  { at: [970, 520], dx: -50, dy: 36, glyph: <path className={s.ink} d={lines([-24, -12, 0, 12, 24].map((x) => [x, 8, x, -8]))} />, link: "M996 506C1070 450 1110 410 1138 364" },
] as const;
const overview: SceneGeometry = {
  desktop: { viewBox: DESKTOP, layers: <>
    <circle className={cx(s.ink, s.faint)} cx={1200} cy={332} r={250} strokeDasharray="2 8" />
    {THEMES.map(({ at, dx, dy, glyph }, index) => <g key={index} transform={`translate(${at[0]} ${at[1]})`}><g className={cx(s.fadeFocus, s.settle)} style={m({ dx, dy, o: 0.85, delay: index * 140 })}>{glyph}</g></g>)}
    {THEMES.map(({ link }, index) => <path key={link} className={cx(s.ink, s.drawLock, s.recede)} style={m({ rest: 0.4, delay: index * 140 })} pathLength={1} d={link} />)}
    <g className={s.lockMark}><circle className={s.accent} cx={1200} cy={332} r={72} opacity={0.5} /><rect className={s.accent} x={1184} y={318} width={32} height={28} rx={3} /></g>
    {THEMES.map(({ link }, index) => <path key={link} className={cx(s.accent, s.trace, [s.w0, s.w1, s.w2, s.w3][index])} strokeWidth={1.75} pathLength={1} d={link} />)}
  </> },
  mobile: { viewBox: MOBILE, layers: <>
    <circle className={cx(s.ink, s.faint)} cx={250} cy={220} r={130} strokeDasharray="2 8" />
    {[[150, 120, -1, -1], [350, 120, 1, -1], [350, 320, 1, 1], [150, 320, -1, 1]].map(([x, y, sx, sy], index) => <g key={index}>
      <circle className={cx(s.node, s.fadeFocus, s.settle)} style={m({ dx: sx * 24, dy: sy * 24, delay: index * 140 })} cx={x} cy={y} r={5} />
      <path className={cx(s.ink, s.drawLock, s.recede)} style={m({ rest: 0.4 })} pathLength={1} d={`M${x} ${y}L${250 - sx * 36} ${220 - sy * 30}`} />
      <path className={cx(s.accent, s.trace, [s.w0, s.w1, s.w2, s.w3][index])} strokeWidth={1.75} pathLength={1} d={`M${x} ${y}L${250 - sx * 36} ${220 - sy * 30}`} />
    </g>)}
    <rect className={cx(s.node, s.lockMark)} x={236} y={207} width={28} height={26} rx={3} />
  </> },
};

/* DECISION ROOM — evidence → question → task → owner → status, resolved stage by stage down the right margin
   (the room's own cards fill the centre). Shapes only, no task text. */
const SPINE = "M1548 170C1530 210 1530 250 1548 290S1566 370 1548 410 1530 490 1548 530 1566 610 1548 650";
const decision: SceneGeometry = {
  desktop: { viewBox: DESKTOP, layers: <>
    <path className={cx(s.dot, s.fadeFocus, s.settle)} style={m({ dy: -40, o: 0.55 })} d={dots([[1524, 120], [1560, 104], [1540, 92]], 2.6)} />
    <path className={cx(s.ink, s.draw, s.recede)} style={m({ rest: 0.5 })} pathLength={1} d="M1548 170C1530 210 1530 250 1548 290" />
    <path className={cx(s.ink, s.drawLock, s.recede)} style={m({ rest: 0.5 })} pathLength={1} d="M1548 290C1566 330 1566 370 1548 410S1530 490 1548 530" />
    <path className={cx(s.ink, s.drawResolve)} pathLength={1} d="M1548 530C1566 570 1566 610 1548 650" />
    <path className={cx(s.node, s.fadeFocus)} d={rects([[1532, 160, 30, 22], [1538, 154, 30, 22]])} />
    <circle className={cx(s.node, s.fadeFocus)} style={m({ delay: 300 })} cx={1548} cy={290} r={13} strokeDasharray="60 22" />
    <rect className={cx(s.node, s.fadeLock)} x={1534} y={396} width={28} height={28} rx={5} />
    <g className={s.fadeLock} style={m({ delay: 300 })}><circle className={s.node} cx={1548} cy={522} r={6} /><path className={s.accent} d="M1534 546C1536 536 1560 536 1562 546" /></g>
    <g className={s.fadeResolve}><circle className={s.node} cx={1548} cy={650} r={14} /><circle className={s.solid} cx={1548} cy={650} r={5} /></g>
    <path className={cx(s.accent, s.trace, s.w0)} strokeWidth={1.75} pathLength={1} d={SPINE} />
  </> },
  mobile: { viewBox: MOBILE, layers: <>
    <path className={cx(s.ink, s.draw, s.recede)} style={m({ rest: 0.5 })} pathLength={1} d="M70 330C120 300 150 240 200 230S300 200 340 160" />
    <path className={cx(s.ink, s.fadeFocus)} d={rects([[56, 318, 26, 22], [62, 312, 26, 22]])} />
    <rect className={cx(s.ink, s.fadeLock)} x={188} y={218} width={24} height={24} rx={5} />
    <g className={s.fadeResolve}><circle className={s.accent} cx={340} cy={160} r={13} /><circle className={s.solid} cx={340} cy={160} r={5} /></g>
    <path className={cx(s.accent, s.trace, s.w0)} strokeWidth={1.75} pathLength={1} d="M70 330C120 300 150 240 200 230S300 200 340 160" />
  </> },
};

/* COMPARE — two identical silhouettes beside the heading, four shared dimensions between them;
   difference marks are symmetric and never crown a side. */
const silhouette = (x: number, base: number, scale = 1) => `M${x - 50 * scale} ${base}V${base - 90 * scale}h${34 * scale}v${-30 * scale}h${32 * scale}v${30 * scale}h${34 * scale}V${base}Z`;
const ROWS = [150, 186, 222, 258];
const GAPS = [[1160, 1240], [1180, 1220], [1145, 1255], [1170, 1230]] as const;
const compare: SceneGeometry = {
  desktop: { viewBox: DESKTOP, layers: <>
    <path className={cx(s.band, s.fadeFocus)} d={`${silhouette(1000, 280)}${silhouette(1400, 280)}`} />
    <path className={cx(s.ink, s.fadeFocus)} d={`${silhouette(1000, 280)}${silhouette(1400, 280)}`} />
    <path className={cx(s.ink, s.faint)} d="M900 280H1500" />
    {ROWS.map((y, index) => <g key={y}>
      <path className={cx(s.ink, s.draw, s.recede)} style={m({ rest: 0.45, delay: index * 140 })} pathLength={1} d={`M1200 ${y}H1070`} />
      <path className={cx(s.ink, s.draw, s.recede)} style={m({ rest: 0.45, delay: index * 140 })} pathLength={1} d={`M1200 ${y}H1330`} />
      <path className={cx(s.accent, s.lockMark)} style={m({ delay: index * 140 })} d={`M${GAPS[index][0]} ${y - 6}v12M${GAPS[index][1]} ${y - 6}v12`} />
      <path className={cx(s.accent, s.halo, [s.w0, s.w1, s.w2, s.w3][index])} strokeWidth={2} d={`M${GAPS[index][0]} ${y}H${GAPS[index][1]}`} />
    </g>)}
  </> },
  mobile: { viewBox: MOBILE, layers: <>
    <path className={cx(s.ink, s.fadeFocus)} d={`${silhouette(218, 196, 0.5)}${silhouette(352, 196, 0.5)}`} />
    {[150, 172].map((y, index) => <g key={y}>
      <path className={cx(s.ink, s.draw, s.recede)} style={m({ rest: 0.45 })} pathLength={1} d={`M285 ${y}H250M285 ${y}H320`} />
      <path className={cx(s.accent, s.halo, [s.w0, s.w1][index])} strokeWidth={2} d={`M${272 - index * 6} ${y}H${298 + index * 6}`} />
    </g>)}
  </> },
};

/* REPORT — three page outlines in the margin beside the report; evidence tokens settle onto citation marks. No text. */
const page = (x: number, y: number) => `M${x} ${y}h140l30 30v200h-170Z`;
const fold = (x: number, y: number) => `M${x + 140} ${y}v30h30`;
const CITES: [number, number][] = [[1556, 236], [1556, 288], [1556, 340]];
const report: SceneGeometry = {
  desktop: { viewBox: DESKTOP, layers: <>
    <path className={cx(s.ink, s.faint, s.fadeFocus)} d={page(1376, 120)} />
    <path className={cx(s.ink, s.faint, s.fadeFocus)} style={m({ delay: 160 })} d={page(1398, 140)} />
    <path className={cx(s.band, s.fadeFocus)} style={m({ delay: 320 })} d={page(1420, 160)} />
    <path className={cx(s.ink, s.draw)} style={m({ delay: 320 })} pathLength={1} d={`${page(1420, 160)}${fold(1420, 160)}`} />
    <path className={cx(s.ink, s.faint, s.fadeLock)} d="M1442 210h72M1442 262h56M1442 314h64" />
    {CITES.map(([x, y], index) => <g key={y}>
      <circle className={cx(s.dot, s.fadeFocus, s.settle, s.recede)} style={m({ dx: -110 - index * 16, dy: 24 - index * 24, o: 0.7, rest: 0.4, delay: index * 160 })} cx={x} cy={y} r={3.5} />
      <path className={cx(s.accent, s.fadeLock)} style={m({ delay: 400 + index * 160 })} d={`M${x - 9} ${y - 8}v16M${x + 9} ${y - 8}v16`} />
    </g>)}
  </> },
  mobile: { viewBox: MOBILE, layers: <>
    <path className={cx(s.ink, s.fadeFocus)} d={page(300, 40)} />
    <path className={cx(s.ink, s.draw)} pathLength={1} d={`${page(318, 58)}${fold(318, 58)}`} />
  </> },
};

/** Home is the photograph itself (children of AmbientScene), so it has no geometry. */
export const SCENES: Record<AmbientVariant, SceneGeometry | null> = { home: null, overview, market, location, risk, finance, decision, compare, report };
