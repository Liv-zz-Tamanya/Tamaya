import {
  Children,
  CSSProperties,
  Fragment,
  ReactNode,
  isValidElement,
  useEffect,
  useState,
} from 'react';
import { createPortal } from 'react-dom';

// Static design canvas — simplified from the prototype's pan/zoom canvas.
// Lays out sections vertically; each section is a horizontal row of artboards.
// Clicking an artboard label opens a focus overlay with ←/→/Esc navigation.

const DC = {
  bg: '#f5f1e8',
  label: 'rgba(60,50,40,0.7)',
  title: 'rgba(40,30,20,0.85)',
  subtitle: 'rgba(60,50,40,0.6)',
  font: '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
};

type ArtboardProps = {
  id: string;
  label: string;
  width?: number;
  height?: number;
  caption?: ReactNode;
  children?: ReactNode;
};

// Marker component — rendered via DCSection
export const DCArtboard = (_props: ArtboardProps) => null;

type SectionProps = {
  id: string;
  title: string;
  subtitle?: string;
  children: ReactNode;
};

function flatten(children: ReactNode): ReactNode[] {
  const out: ReactNode[] = [];
  Children.forEach(children, (c) => {
    if (isValidElement(c) && c.type === Fragment) {
      out.push(...flatten((c.props as { children: ReactNode }).children));
    } else {
      out.push(c);
    }
  });
  return out;
}

type FocusState = { sectionIdx: number; artIdx: number } | null;

type CanvasCtx = {
  setFocus: (s: FocusState) => void;
  sections: { id: string; title: string; artboards: ArtboardProps[] }[];
};

export const DesignCanvas = ({ children }: { children: ReactNode }) => {
  const [focus, setFocus] = useState<FocusState>(null);

  // Collect section + artboard metadata for focus navigation
  const sections = flatten(children)
    .filter(
      (c): c is React.ReactElement<SectionProps> =>
        isValidElement(c) && (c.type as { displayName?: string }).displayName === 'DCSection',
    )
    .map((sec) => ({
      id: sec.props.id,
      title: sec.props.title,
      subtitle: sec.props.subtitle,
      artboards: flatten(sec.props.children)
        .filter(
          (a): a is React.ReactElement<ArtboardProps> =>
            isValidElement(a) && a.type === DCArtboard,
        )
        .map((a) => a.props),
    }));

  const ctx: CanvasCtx = { setFocus, sections };

  useEffect(() => {
    if (!focus) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setFocus(null);
        return;
      }
      const { sectionIdx, artIdx } = focus;
      const sec = sections[sectionIdx];
      if (!sec) return;
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault();
        const d = e.key === 'ArrowLeft' ? -1 : 1;
        const next = (artIdx + d + sec.artboards.length) % sec.artboards.length;
        setFocus({ sectionIdx, artIdx: next });
      }
      if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
        e.preventDefault();
        const d = e.key === 'ArrowUp' ? -1 : 1;
        let nextSec = sectionIdx;
        for (let i = 1; i <= sections.length; i++) {
          const ns = (((sectionIdx + d * i) % sections.length) + sections.length) % sections.length;
          if (sections[ns].artboards.length) {
            nextSec = ns;
            break;
          }
        }
        setFocus({ sectionIdx: nextSec, artIdx: 0 });
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [focus, sections]);

  return (
    <div
      className="design-canvas"
      style={{
        minHeight: '100vh',
        background: DC.bg,
        fontFamily: DC.font,
        padding: '48px 0 96px',
      }}
    >
      {Children.map(children, (child) => {
        if (
          !isValidElement(child) ||
          (child.type as { displayName?: string }).displayName !== 'DCSection'
        ) {
          return child;
        }
        const sectionIdx = sections.findIndex((s) => s.id === (child.props as SectionProps).id);
        return <SectionRenderer ctx={ctx} sectionIdx={sectionIdx} {...(child.props as SectionProps)} />;
      })}
      {focus && (
        <FocusOverlay
          ctx={ctx}
          focus={focus}
          onClose={() => setFocus(null)}
          onGo={(s) => setFocus(s)}
        />
      )}
    </div>
  );
};

const SectionRenderer = ({
  ctx,
  sectionIdx,
  id,
  title,
  subtitle,
  children,
}: SectionProps & { ctx: CanvasCtx; sectionIdx: number }) => {
  const artboards = flatten(children).filter(
    (a): a is React.ReactElement<ArtboardProps> => isValidElement(a) && a.type === DCArtboard,
  );
  const rest = flatten(children).filter(
    (a) => !(isValidElement(a) && a.type === DCArtboard),
  );

  return (
    <section data-dc-section={id} style={{ marginBottom: 80, position: 'relative' }}>
      <div style={{ padding: '0 60px 24px' }}>
        <h2
          style={{
            fontSize: 28,
            fontWeight: 600,
            color: DC.title,
            letterSpacing: -0.4,
            margin: '0 0 6px',
            display: 'inline-block',
          }}
        >
          {title}
        </h2>
        {subtitle && <div style={{ fontSize: 16, color: DC.subtitle }}>{subtitle}</div>}
      </div>
      <div
        style={{
          display: 'flex',
          gap: 48,
          padding: '0 60px',
          alignItems: 'flex-start',
          overflowX: 'auto',
          paddingBottom: 12,
        }}
      >
        {artboards.map((ab, i) => (
          <ArtboardFrame
            key={ab.props.id}
            ctx={ctx}
            sectionIdx={sectionIdx}
            artIdx={i}
            {...ab.props}
          />
        ))}
      </div>
      {rest.length > 0 && <div style={{ padding: '0 60px' }}>{rest}</div>}
    </section>
  );
};

// Required so DesignCanvas can find sections regardless of named-export imports
type DCSectionFC = (props: SectionProps) => JSX.Element;
export const DCSection: DCSectionFC = ({ children }) => <>{children}</>;
(DCSection as unknown as { displayName: string }).displayName = 'DCSection';

const ArtboardFrame = ({
  ctx,
  sectionIdx,
  artIdx,
  id,
  label,
  width = 260,
  height = 480,
  children,
  caption,
}: ArtboardProps & { ctx: CanvasCtx; sectionIdx: number; artIdx: number }) => {
  const cardStyle: CSSProperties = {
    width,
    height,
    background: '#fff',
    borderRadius: 2,
    boxShadow: '0 1px 3px rgba(0,0,0,.08), 0 4px 16px rgba(0,0,0,.06)',
    overflow: 'hidden',
    position: 'relative',
  };

  return (
    <div data-dc-slot={id} style={{ position: 'relative', flexShrink: 0 }}>
      <button
        type="button"
        onClick={() => ctx.setFocus({ sectionIdx, artIdx })}
        style={{
          background: 'transparent',
          border: 'none',
          padding: '3px 6px',
          fontSize: 15,
          fontWeight: 500,
          color: DC.label,
          fontFamily: 'inherit',
          cursor: 'pointer',
          marginBottom: 4,
          textAlign: 'left',
          display: 'block',
        }}
        title="클릭하여 확대"
      >
        {label}
      </button>
      <div className="dc-card" style={cardStyle}>
        {children}
      </div>
      {caption && (
        <div
          style={{
            width,
            marginTop: 14,
            fontFamily: '"Patrick Hand", "Gaegu", sans-serif',
            fontSize: 14,
            lineHeight: 1.45,
            color: '#3a342c',
            paddingLeft: 10,
            borderLeft: '2px solid #8c4a1f',
          }}
        >
          {caption}
        </div>
      )}
    </div>
  );
};

const FocusOverlay = ({
  ctx,
  focus,
  onClose,
  onGo,
}: {
  ctx: CanvasCtx;
  focus: { sectionIdx: number; artIdx: number };
  onClose: () => void;
  onGo: (f: FocusState) => void;
}) => {
  const sec = ctx.sections[focus.sectionIdx];
  const ab = sec?.artboards[focus.artIdx];
  if (!ab) return null;

  const [vp, setVp] = useState({ w: window.innerWidth, h: window.innerHeight });
  useEffect(() => {
    const r = () => setVp({ w: window.innerWidth, h: window.innerHeight });
    window.addEventListener('resize', r);
    return () => window.removeEventListener('resize', r);
  }, []);

  const w = ab.width ?? 260;
  const h = ab.height ?? 480;
  const scale = Math.max(0.1, Math.min((vp.w - 200) / w, (vp.h - 260) / h, 2));

  return createPortal(
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 100,
        background: 'rgba(24,20,16,.65)',
        backdropFilter: 'blur(14px)',
        fontFamily: DC.font,
        color: '#fff',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 72,
          display: 'flex',
          alignItems: 'center',
          padding: '0 20px',
          gap: 16,
        }}
      >
        <div style={{ fontSize: 18, fontWeight: 600 }}>{sec.title}</div>
        <div style={{ flex: 1 }} />
        <button
          onClick={onClose}
          style={{
            border: 'none',
            background: 'transparent',
            color: 'rgba(255,255,255,.7)',
            width: 32,
            height: 32,
            borderRadius: 16,
            fontSize: 22,
            cursor: 'pointer',
            lineHeight: 1,
          }}
        >
          ×
        </button>
      </div>

      <div
        style={{
          position: 'absolute',
          top: 64,
          bottom: 56,
          left: 100,
          right: 100,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 16,
        }}
      >
        <div onClick={(e) => e.stopPropagation()} style={{ width: w * scale, height: h * scale }}>
          <div
            style={{
              width: w,
              height: h,
              transform: `scale(${scale})`,
              transformOrigin: 'top left',
              background: '#fff',
              borderRadius: 2,
              overflow: 'hidden',
              boxShadow: '0 20px 80px rgba(0,0,0,.4)',
            }}
          >
            {ab.children}
          </div>
        </div>
        <div onClick={(e) => e.stopPropagation()} style={{ fontSize: 14, opacity: 0.85 }}>
          {ab.label}
          <span style={{ opacity: 0.5, marginLeft: 10 }}>
            {focus.artIdx + 1} / {sec.artboards.length}
          </span>
        </div>
      </div>

      {/* Prev/Next arrows */}
      {(['left', 'right'] as const).map((dir) => (
        <button
          key={dir}
          onClick={(e) => {
            e.stopPropagation();
            const d = dir === 'left' ? -1 : 1;
            const next = (focus.artIdx + d + sec.artboards.length) % sec.artboards.length;
            onGo({ sectionIdx: focus.sectionIdx, artIdx: next });
          }}
          style={{
            position: 'absolute',
            top: '50%',
            [dir]: 28,
            transform: 'translateY(-50%)',
            border: 'none',
            background: 'rgba(255,255,255,.08)',
            color: 'rgba(255,255,255,.9)',
            width: 44,
            height: 44,
            borderRadius: 22,
            fontSize: 18,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {dir === 'left' ? '‹' : '›'}
        </button>
      ))}

      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'absolute',
          bottom: 20,
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
          gap: 8,
        }}
      >
        {sec.artboards.map((p, i) => (
          <button
            key={p.id}
            onClick={() => onGo({ sectionIdx: focus.sectionIdx, artIdx: i })}
            style={{
              border: 'none',
              padding: 0,
              cursor: 'pointer',
              width: 6,
              height: 6,
              borderRadius: 3,
              background: i === focus.artIdx ? '#fff' : 'rgba(255,255,255,.3)',
            }}
          />
        ))}
      </div>
    </div>,
    document.body,
  );
};
