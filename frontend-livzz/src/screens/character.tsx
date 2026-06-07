import { useState } from 'react';
import { CatSketch, ImgPh, StatusBar, TabBar } from '../components/primitives';
import { useNav } from '../lib/router';

// 18-20 · Cat Room / Inventory · Wardrobe / Weekly Report

export const S18_CatRoom = () => {
  const nav = useNav();
  const [toast, setToast] = useState<string | null>(null);
  const flash = (m: string) => {
    setToast(m);
    setTimeout(() => setToast(null), 1400);
  };
  return (
  <div
    className="phone-inner"
    style={{
      background: 'linear-gradient(180deg, #2b1810 0%, #4a2f1e 70%, #2b1810 100%)',
      color: '#f5e6cf',
    }}
  >
    <StatusBar mode="night" time="10:42 PM" />
    <div
      style={{
        position: 'absolute',
        top: 44,
        left: 0,
        right: 0,
        height: 360,
        overflow: 'hidden',
      }}
    >
      <svg width="100%" height="100%" viewBox="0 0 375 360" preserveAspectRatio="none">
        <rect
          x="34"
          y="40"
          width="120"
          height="100"
          fill="#1a0e08"
          stroke="#f5e6cf"
          strokeWidth="2"
        />
        <line x1="94" y1="40" x2="94" y2="140" stroke="#f5e6cf" strokeWidth="1.5" />
        <line x1="34" y1="90" x2="154" y2="90" stroke="#f5e6cf" strokeWidth="1.5" />
        {[
          [60, 60],
          [120, 72],
          [80, 108],
          [130, 118],
        ].map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r="1.5" fill="#f5e6cf" />
        ))}
        <text x="40" y="160" fontFamily="Patrick Hand" fontSize="10" fill="#d8a777">
          창문 (밤)
        </text>

        <line x1="180" y1="120" x2="345" y2="120" stroke="#f5e6cf" strokeWidth="2" />
        <rect
          x="200"
          y="100"
          width="20"
          height="20"
          fill="none"
          stroke="#f5e6cf"
          strokeWidth="1.5"
        />
        <circle cx="240" cy="110" r="10" fill="none" stroke="#f5e6cf" strokeWidth="1.5" />
        <path
          d="M270 120 L 270 100 L 290 100 L 290 120 Z"
          fill="none"
          stroke="#f5e6cf"
          strokeWidth="1.5"
        />
        <text x="200" y="138" fontFamily="Patrick Hand" fontSize="10" fill="#d8a777">
          선반 · 모은 아이템
        </text>

        <line x1="0" y1="280" x2="375" y2="280" stroke="#f5e6cf" strokeWidth="2" />

        <ellipse
          cx="160"
          cy="290"
          rx="120"
          ry="14"
          fill="none"
          stroke="#8c4a1f"
          strokeWidth="1.5"
          strokeDasharray="3 3"
        />

        <ellipse
          cx="80"
          cy="282"
          rx="22"
          ry="8"
          fill="#f5e6cf"
          stroke="#3a2414"
          strokeWidth="2"
        />
        <path
          d="M60 282 Q 80 274 100 282"
          stroke="#3a2414"
          strokeWidth="1.5"
          fill="none"
        />
        <text x="50" y="300" fontFamily="Patrick Hand" fontSize="10" fill="#d8a777">
          밥그릇
        </text>

        <rect
          x="250"
          y="260"
          width="100"
          height="30"
          rx="14"
          fill="#f5e6cf"
          stroke="#3a2414"
          strokeWidth="2"
        />
        <text x="270" y="310" fontFamily="Patrick Hand" fontSize="10" fill="#d8a777">
          방석
        </text>
      </svg>

      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: 170,
          transform: 'translateX(-50%)',
        }}
      >
        <div
          style={{
            background: '#f5e6cf',
            border: '2px solid #3a2414',
            borderRadius: 16,
            padding: 8,
          }}
        >
          <CatSketch size={110} mood="wink" />
        </div>
        <div
          className="handwriting"
          style={{ fontSize: 18, textAlign: 'center', marginTop: 4, color: '#f5e6cf' }}
        >
          "고마워 ♡"
        </div>
      </div>

      <div style={{ position: 'absolute', left: 30, top: 200 }}>
        <span className="chip" style={{ background: '#f5e6cf', color: '#3a2414' }}>
          👕 줄무늬 스카프
        </span>
      </div>
    </div>

    <div
      style={{
        position: 'absolute',
        top: 50,
        left: 14,
        right: 14,
        display: 'flex',
        justifyContent: 'space-between',
      }}
    >
      <div className="chip" style={{ background: '#f5e6cf', color: '#3a2414' }}>
        이음이 · Lv.3
      </div>
      <div style={{ display: 'flex', gap: 6 }}>
        <span className="chip" style={{ background: '#f5e6cf', color: '#3a2414' }}>
          ◉ 240
        </span>
        <span className="chip" style={{ background: '#f5e6cf', color: '#3a2414' }}>
          ♡ 8/10
        </span>
      </div>
    </div>

    <div style={{ position: 'absolute', top: 408, left: 18, right: 18 }}>
      <div
        className="hbox r-l"
        style={{ padding: 12, background: '#f5e6cf', color: '#3a2414' }}
      >
        <div className="h-section">친밀도 & 컨디션</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
          {(
            [
              ['♡ 친밀도', '80%', '#8c4a1f'],
              ['◍ 배부름', '55%', '#c9a266'],
              ['☼ 활력', '65%', '#7a5634'],
            ] as [string, string, string][]
          ).map(([n, p, c], i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontFamily: 'Patrick Hand', fontSize: 12, width: 70 }}>{n}</span>
              <div className="bar" style={{ flex: 1 }}>
                <i style={{ width: p, background: c }} />
              </div>
              <span className="tiny" style={{ width: 36, textAlign: 'right' }}>
                {p}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 8,
          marginTop: 10,
        }}
      >
        {(
          [
            ['🍖', '먹이주기', () => flash('냠냠 🐟 배부름이 올랐어요')],
            ['👕', '옷장', () => nav.go('inventory')],
            ['◐', '놀이', () => flash('꺄르륵! 활력이 올랐어요 ✦')],
            ['◰', '방꾸미기', () => nav.go('inventory')],
          ] as [string, string, () => void][]
        ).map(([ic, t, onAct], i) => (
          <button
            key={i}
            type="button"
            className="hbox"
            onClick={onAct}
            style={{
              padding: 10,
              textAlign: 'center',
              background: '#f5e6cf',
              color: '#3a2414',
              cursor: 'pointer',
              fontFamily: 'inherit',
            }}
          >
            <div style={{ fontSize: 22 }}>{ic}</div>
            <div className="tiny" style={{ marginTop: 2 }}>
              {t}
            </div>
          </button>
        ))}
      </div>

      <div className="sticky" style={{ marginTop: 10, color: '#3a2414' }}>
        tip — 회고 자주 할수록 친밀도 ↑, 새 옷 잠금해제
      </div>
    </div>
    {toast && <div className="toast">{toast}</div>}
    <TabBar active="cat" />
  </div>
  );
};

export const S19_Inventory = () => {
  const nav = useNav();
  return (
  <div className="phone-inner">
    <StatusBar mode="day" time="11:30 AM" />
    <div className="phone-scroll" style={{ padding: '46px 18px 140px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span
          style={{ fontFamily: 'Caveat', fontSize: 22, cursor: 'pointer' }}
          onClick={() => nav.back()}
        >
          ‹
        </span>
        <div className="h-title">인벤토리 / 옷장</div>
      </div>
      <div className="tiny">모은 아이템 · 24개 · 240 포인트</div>

      <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
        {['전체', '👕 옷', '🎩 모자', '🍖 먹이', '◰ 방', '🎁 보상'].map((t, i) => (
          <span key={i} className={'chip ' + (i === 1 ? 'solid' : '')}>
            {t}
          </span>
        ))}
      </div>

      <div className="hbox r-l" style={{ padding: 12, marginTop: 12 }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 8,
          }}
        >
          {(
            [
              ['🧣 스카프', '7일 스트릭', true, true],
              ['👕 줄무늬', '5월 보상', true, false],
              ['🎩 베레모', 'Lv.5', false, false],
              ['🦺 조끼', '14일', false, false],
              ['🥽 안경', '30일', false, false],
              ['👔 셔츠', '월간 리포트', false, false],
            ] as [string, string, boolean, boolean][]
          ).map(([n, sub, have, eq], i) => (
            <div
              key={i}
              className="hbox dashed"
              style={{
                padding: 10,
                position: 'relative',
                background: have ? '#fff' : 'rgba(0,0,0,0.04)',
                opacity: have ? 1 : 0.6,
              }}
            >
              <ImgPh h={64} label={have ? '아이템' : '잠금'} />
              <div
                style={{
                  fontFamily: 'Patrick Hand',
                  fontWeight: 700,
                  fontSize: 13,
                  marginTop: 6,
                }}
              >
                {n}
              </div>
              <div className="tiny">{sub}</div>
              {eq && (
                <span
                  className="chip accent"
                  style={{ position: 'absolute', top: -8, right: -8, fontSize: 10 }}
                >
                  입는중
                </span>
              )}
              {!have && (
                <span
                  style={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    fontSize: 16,
                  }}
                >
                  🔒
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="h-label" style={{ marginTop: 14, marginBottom: 6 }}>
        먹이 · 7개
      </div>
      <div style={{ display: 'flex', gap: 8, overflowX: 'hidden' }}>
        {(
          [
            ['🐟 츄르 (참치)', 5],
            ['🍗 닭가슴', 3],
            ['🥛 우유', 2],
            ['🍰 케이크', 1],
          ] as [string, number][]
        ).map(([n, c], i) => (
          <div
            key={i}
            className="hbox"
            style={{ padding: 8, minWidth: 92, textAlign: 'center', flex: 'none' }}
          >
            <div style={{ fontSize: 22 }}>{n.split(' ')[0]}</div>
            <div className="tiny">{n.split(' ').slice(1).join(' ')}</div>
            <div style={{ fontFamily: 'Patrick Hand', fontWeight: 700, fontSize: 13 }}>
              × {c}
            </div>
          </div>
        ))}
      </div>
    </div>
    <div style={{ position: 'absolute', bottom: 78, left: 18, right: 18 }}>
      <button
        type="button"
        onClick={() => nav.back()}
        className="btn primary block"
        style={{ cursor: 'pointer', fontFamily: 'inherit' }}
      >
        선택 입히기
      </button>
    </div>
    <TabBar active="cat" />
  </div>
  );
};

export const S20_Report = () => {
  const nav = useNav();
  return (
  <div className="phone-inner">
    <StatusBar mode="day" time="9:08 AM" />
    <div className="phone-scroll" style={{ padding: '46px 18px 88px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span
          style={{ fontFamily: 'Caveat', fontSize: 22, cursor: 'pointer' }}
          onClick={() => nav.back()}
        >
          ‹
        </span>
        <div className="h-section">주간 리포트 — 매주 월요일</div>
      </div>
      <div className="h-display" style={{ marginTop: 6, fontSize: 30 }}>
        5월 4째주
        <br />
        너의 일주일.
      </div>
      <div className="tiny" style={{ marginTop: 4 }}>
        5/19 — 5/25 · 6일 기록 · 1일 휴식
      </div>

      <div
        className="hbox r-l"
        style={{ padding: 14, marginTop: 14, background: '#fff5e1' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <CatSketch size={70} mood="happy" />
          <div>
            <div className="h-section">한 줄 요약</div>
            <div className="handwriting" style={{ fontSize: 18 }}>
              "피곤한 주, 그래도 잘 버텼어"
            </div>
          </div>
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 8,
          marginTop: 12,
        }}
      >
        {(
          [
            ['일기', '6', '회'],
            ['평균 수면', '6.4', '시간'],
            ['이번 주 감정', '😌', '평온'],
            ['포인트', '+ 280', '◉'],
            ['스트릭', '12', '일'],
            ['새 아이템', '2', '개'],
          ] as [string, string, string][]
        ).map(([t, n, u], i) => (
          <div
            key={i}
            className={'hbox ' + (i % 2 ? 'r-r' : 'r-l')}
            style={{ padding: 10, textAlign: 'center' }}
          >
            <div className="tiny">{t}</div>
            <div
              style={{
                fontFamily: 'Caveat',
                fontWeight: 700,
                fontSize: 26,
                marginTop: 2,
              }}
            >
              {n}
            </div>
            <div className="tiny">{u}</div>
          </div>
        ))}
      </div>

      <div className="hbox r-r" style={{ padding: 14, marginTop: 12 }}>
        <div className="h-section">이번 주 이야기</div>
        <div className="body" style={{ marginTop: 6, lineHeight: 1.6 }}>
          월·화에 회의가 길어 피곤이 컸어요.
          <br />
          수요일에 산책을 다시 시작한 뒤로
          <br />
          평온함이 늘었어요. 같은 패턴을 이어가요.
        </div>
      </div>

      <div
        className="hbox night r-l"
        style={{
          padding: 12,
          marginTop: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
        }}
      >
        <div className="ph-circle" style={{ width: 36, height: 36, background: '#fff' }}>
          ◇
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: 'Patrick Hand', fontWeight: 700, color: '#fff' }}>
            리포트 카드 저장
          </div>
          <div className="tiny" style={{ color: '#d8a777' }}>
            나만 보기 / 이미지로 내보내기
          </div>
        </div>
        <span style={{ fontFamily: 'Caveat', fontSize: 22, color: '#fff' }}>›</span>
      </div>
    </div>
    <TabBar active="ins" />
  </div>
  );
};
