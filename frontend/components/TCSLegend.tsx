'use client';

/** Konstanta warna TCS yang dipakai bersama oleh MapView dan TCSLegend. */
export const TCS_GRADES = [
  { min: 0.0, max: 0.3, color: '#e63946', label: 'Sangat Panas', emoji: '🔴' },
  { min: 0.3, max: 0.5, color: '#f4a261', label: 'Panas',        emoji: '🟠' },
  { min: 0.5, max: 0.7, color: '#e9c46a', label: 'Sedang',       emoji: '🟡' },
  { min: 0.7, max: 1.0, color: '#1a936f', label: 'Nyaman',       emoji: '🟢' },
] as const;

/** Ambil warna hex berdasarkan nilai TCS */
export function tcsToColor(tcs: number): string {
  if (tcs >= 0.7) return '#1a936f';
  if (tcs >= 0.5) return '#e9c46a';
  if (tcs >= 0.3) return '#f4a261';
  return '#e63946';
}

/** Ambil label grade berdasarkan nilai TCS */
export function tcsToLabel(tcs: number): string {
  if (tcs >= 0.7) return 'Nyaman';
  if (tcs >= 0.5) return 'Sedang';
  if (tcs >= 0.3) return 'Panas';
  return 'Sangat Panas';
}

/** Ambil warna Mantine badge berdasarkan nilai TCS */
export function tcsToBadgeColor(tcs: number): string {
  if (tcs >= 0.7) return 'green';
  if (tcs >= 0.5) return 'yellow';
  if (tcs >= 0.3) return 'orange';
  return 'red';
}

interface TCSLegendProps {
  /** Tampilkan di atas elemen lain */
  style?: React.CSSProperties;
}

/** Legenda TCS untuk ditampilkan di pojok peta */
export default function TCSLegend({ style }: TCSLegendProps) {
  return (
    <div
      style={{
        background: 'rgba(255,255,255,0.92)',
        borderRadius: 10,
        padding: '8px 12px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.12)',
        backdropFilter: 'blur(4px)',
        minWidth: 160,
        ...style,
      }}
    >
      <div style={{ fontSize: 10, fontWeight: 700, color: '#666', marginBottom: 6, letterSpacing: '0.05em' }}>
        KENYAMANAN JALAN (TCS)
      </div>
      {TCS_GRADES.map((grade) => (
        <div
          key={grade.label}
          style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}
        >
          <div
            style={{
              width: 28,
              height: 5,
              borderRadius: 3,
              background: grade.color,
              flexShrink: 0,
            }}
          />
          <span style={{ fontSize: 11, color: '#333', lineHeight: 1.2 }}>
            <span style={{ fontWeight: 600 }}>{grade.label}</span>
            <span style={{ color: '#888', marginLeft: 4 }}>
              {grade.min.toFixed(1)}–{grade.max.toFixed(1)}
            </span>
          </span>
        </div>
      ))}
    </div>
  );
}
