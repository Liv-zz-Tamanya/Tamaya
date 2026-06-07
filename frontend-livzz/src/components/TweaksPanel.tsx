import { useEffect, useState } from 'react';

// Tamaya tweaks — palette / vibe / density toggle (top-right fixed panel)
// 4 palette presets reshape CSS variables. Vibe + density flip body[data-*]
// classes — every screen re-tones in lockstep via CSS.

type Palette = 'coffee' | 'matcha' | 'wine' | 'lavender';
type Vibe = 'sketchy' | 'crisp' | 'playful';
type Density = 'minimal' | 'standard' | 'detailed';

const PALETTES: Record<
  Palette,
  { label: string; swatch: string[]; vars: Record<string, string> }
> = {
  coffee: {
    label: 'Coffee Lounge',
    swatch: ['#8c4a1f', '#2b1810', '#f5e6cf', '#d8a777'],
    vars: {
      '--paper': '#f5e6cf',
      '--paper-2': '#ead0a6',
      '--paper-3': '#e0c08c',
      '--ink': '#3a2414',
      '--ink-soft': '#5a3a22',
      '--accent': '#8c4a1f',
      '--accent-soft': '#d8a777',
      '--accent-2': '#a66838',
      '--night': '#2b1810',
      '--night-2': '#3d2618',
      '--night-soft': '#d8a777',
      '--day': '#b8804a',
      '--day-soft': '#f0d9b5',
      '--cream': '#fff5e1',
      '--line': '#c9a877',
      '--pencil': '#7a5634',
      '--muted': '#b39570',
      '--good': '#6b5a3a',
      '--good-soft': '#d9c69e',
    },
  },
  matcha: {
    label: 'Matcha Studio',
    swatch: ['#5a7a3d', '#1f2818', '#eef0d8', '#b8c785'],
    vars: {
      '--paper': '#eef0d8',
      '--paper-2': '#d8dfb0',
      '--paper-3': '#b9c886',
      '--ink': '#2d3320',
      '--ink-soft': '#4a5232',
      '--accent': '#5a7a3d',
      '--accent-soft': '#b8c785',
      '--accent-2': '#7a9550',
      '--night': '#1f2818',
      '--night-2': '#2e3a23',
      '--night-soft': '#b8c785',
      '--day': '#8aa860',
      '--day-soft': '#dde5b5',
      '--cream': '#f7f8e6',
      '--line': '#a0b069',
      '--pencil': '#5a684a',
      '--muted': '#90a070',
      '--good': '#5a684a',
      '--good-soft': '#cad59a',
    },
  },
  wine: {
    label: 'Wine Bar',
    swatch: ['#8a2c33', '#1e0e10', '#f3e4dc', '#c79a9a'],
    vars: {
      '--paper': '#f3e4dc',
      '--paper-2': '#e2c7be',
      '--paper-3': '#c89b8d',
      '--ink': '#2e1818',
      '--ink-soft': '#4a2828',
      '--accent': '#8a2c33',
      '--accent-soft': '#c79a9a',
      '--accent-2': '#a3464e',
      '--night': '#1e0e10',
      '--night-2': '#2d1a1c',
      '--night-soft': '#c79a9a',
      '--day': '#b4555f',
      '--day-soft': '#e8c8c8',
      '--cream': '#fff0eb',
      '--line': '#c08a85',
      '--pencil': '#6d3a3a',
      '--muted': '#b08585',
      '--good': '#6d3a3a',
      '--good-soft': '#dba8a8',
    },
  },
  lavender: {
    label: 'Lavender Library',
    swatch: ['#6a4a8a', '#1a1428', '#efe8f3', '#c4abd8'],
    vars: {
      '--paper': '#efe8f3',
      '--paper-2': '#d8c9e0',
      '--paper-3': '#b8a4c5',
      '--ink': '#2a213a',
      '--ink-soft': '#443758',
      '--accent': '#6a4a8a',
      '--accent-soft': '#c4abd8',
      '--accent-2': '#836bb3',
      '--night': '#1a1428',
      '--night-2': '#2a2240',
      '--night-soft': '#c4abd8',
      '--day': '#9b80c0',
      '--day-soft': '#d8c4e8',
      '--cream': '#f9f2ff',
      '--line': '#b09bc5',
      '--pencil': '#5a4670',
      '--muted': '#a08bb5',
      '--good': '#5a4670',
      '--good-soft': '#cbb8d8',
    },
  },
};

const LS_KEY = 'tamaya-tweaks-v1';

const load = () => {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as { palette: Palette; vibe: Vibe; density: Density };
  } catch {
    return null;
  }
};

export const TweaksPanel = () => {
  const initial = load() ?? { palette: 'coffee' as Palette, vibe: 'crisp' as Vibe, density: 'detailed' as Density };
  const [palette, setPalette] = useState<Palette>(initial.palette);
  const [vibe, setVibe] = useState<Vibe>(initial.vibe);
  const [density, setDensity] = useState<Density>(initial.density);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const pal = PALETTES[palette];
    Object.entries(pal.vars).forEach(([k, v]) =>
      document.documentElement.style.setProperty(k, v),
    );
    document.documentElement.dataset.palette = palette;
  }, [palette]);

  useEffect(() => {
    document.body.dataset.vibe = vibe;
  }, [vibe]);

  useEffect(() => {
    document.body.dataset.density = density;
  }, [density]);

  useEffect(() => {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify({ palette, vibe, density }));
    } catch {
      // ignore quota errors
    }
  }, [palette, vibe, density]);

  return (
    <div
      style={{
        position: 'fixed',
        top: 16,
        right: 16,
        zIndex: 50,
        fontFamily: '-apple-system, BlinkMacSystemFont, system-ui, sans-serif',
      }}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        style={{
          background: '#fff',
          border: '1.5px solid #3a2414',
          borderRadius: 10,
          padding: '8px 14px',
          fontSize: 13,
          fontWeight: 600,
          cursor: 'pointer',
          fontFamily: 'inherit',
          boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
          color: '#3a2414',
        }}
      >
        ⚙ Tamaya · Tweaks {open ? '▴' : '▾'}
      </button>

      {open && (
        <div
          style={{
            marginTop: 8,
            background: '#fff',
            border: '1.5px solid #3a2414',
            borderRadius: 12,
            padding: 16,
            width: 280,
            boxShadow: '0 6px 24px rgba(0,0,0,0.12)',
          }}
        >
          <div style={{ fontSize: 11, opacity: 0.6, marginBottom: 6, letterSpacing: 0.4 }}>
            팔레트 · MOOD
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {(Object.entries(PALETTES) as [Palette, (typeof PALETTES)[Palette]][]).map(
              ([k, p]) => (
                <button
                  key={k}
                  onClick={() => setPalette(k)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '6px 8px',
                    background: palette === k ? '#f5e6cf' : 'transparent',
                    border: '1px solid ' + (palette === k ? '#8c4a1f' : 'transparent'),
                    borderRadius: 6,
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                    fontSize: 13,
                    textAlign: 'left',
                  }}
                >
                  <div style={{ display: 'flex', gap: 2 }}>
                    {p.swatch.map((c, i) => (
                      <div
                        key={i}
                        style={{
                          width: 14,
                          height: 14,
                          background: c,
                          borderRadius: 3,
                          border: '0.5px solid rgba(0,0,0,0.15)',
                        }}
                      />
                    ))}
                  </div>
                  <span>{p.label}</span>
                </button>
              ),
            )}
          </div>

          <div
            style={{ fontSize: 11, opacity: 0.6, marginTop: 14, marginBottom: 6, letterSpacing: 0.4 }}
          >
            Vibe · 분위기 강도
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {(['sketchy', 'crisp', 'playful'] as Vibe[]).map((v) => (
              <button
                key={v}
                onClick={() => setVibe(v)}
                style={{
                  flex: 1,
                  padding: '6px 0',
                  background: vibe === v ? '#3a2414' : '#fff',
                  color: vibe === v ? '#f5e6cf' : '#3a2414',
                  border: '1px solid #3a2414',
                  borderRadius: 6,
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                  fontSize: 12,
                }}
              >
                {v}
              </button>
            ))}
          </div>

          <div
            style={{ fontSize: 11, opacity: 0.6, marginTop: 14, marginBottom: 6, letterSpacing: 0.4 }}
          >
            Density · 정보 밀도
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {(['minimal', 'standard', 'detailed'] as Density[]).map((d) => (
              <button
                key={d}
                onClick={() => setDensity(d)}
                style={{
                  flex: 1,
                  padding: '6px 0',
                  background: density === d ? '#3a2414' : '#fff',
                  color: density === d ? '#f5e6cf' : '#3a2414',
                  border: '1px solid #3a2414',
                  borderRadius: 6,
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                  fontSize: 12,
                }}
              >
                {d}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
