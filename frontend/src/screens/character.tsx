import { useState } from 'react';
import { BackButton, CatSketch, ImgPh, TabBar, useToast } from '../components/primitives';
import { useNav } from '../lib/router';
import { MOOD_LABEL, isWithinLastWeek, latestEntry, useStore } from '../lib/store';

// 18-20 · Cat Room / Inventory · Wardrobe / Weekly Report

export const S18_CatRoom = () => {
  const nav = useNav();
  const { state } = useStore();
  const { toast, flash } = useToast();
  // 친밀도=회고 연속일 비례(읽기) · 배부름/활력=먹이/놀이로 반응(세션 인터랙션). (C)경계 로컬.
  const intimacy = Math.min(100, 20 + state.streak * 6);
  const [satiety, setSatiety] = useState(55);
  const [vitality, setVitality] = useState(65);
  return (
  <div
    className="screen"
    style={{
      background: 'linear-gradient(180deg, var(--night) 0%, var(--night-2) 68%, var(--night) 100%)',
      color: 'var(--paper)',
    }}
  >
    <div className="screen-scroll" style={{ paddingBottom: 'calc(88px + var(--safe-b, 0px))' }}>
    <div className="stage-body">
    <div
      style={{
        position: 'absolute',
        top: 44,
        left: 0,
        right: 0,
        maxHeight: 360,
        height: 'min(360px, 45dvh)',
        overflow: 'hidden',
      }}
    >
      <svg width="100%" height="100%" viewBox="0 0 375 360" preserveAspectRatio="xMidYMid slice">
        <rect
          x="34"
          y="40"
          width="120"
          height="100"
          rx="14"
          fill="var(--night-2)"
          stroke="var(--paper)"
          strokeWidth="1.5"
        />
        {[
          [60, 60],
          [120, 72],
          [80, 108],
          [130, 118],
        ].map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r="1.5" fill="var(--paper)" />
        ))}
        <text x="40" y="160" fontFamily="Pretendard" fontSize="10" fill="var(--accent-soft)">
          창문 (밤)
        </text>

        <line x1="180" y1="120" x2="345" y2="120" stroke="var(--paper)" strokeWidth="2" strokeLinecap="round" />
        <rect
          x="200"
          y="100"
          width="20"
          height="20"
          rx="4"
          fill="var(--night-2)"
          stroke="var(--paper)"
          strokeWidth="1.5"
        />
        <circle cx="240" cy="110" r="10" fill="none" stroke="var(--paper)" strokeWidth="1.5" />
        <path
          d="M270 120 L 270 100 L 290 100 L 290 120 Z"
          fill="var(--night-2)"
          stroke="var(--paper)"
          strokeWidth="1.5"
        />
        <text x="200" y="138" fontFamily="Pretendard" fontSize="10" fill="var(--accent-soft)">
          선반 · 모은 아이템
        </text>

        <line x1="0" y1="280" x2="375" y2="280" stroke="var(--paper)" strokeWidth="2" />

        <ellipse
          cx="160"
          cy="290"
          rx="120"
          ry="14"
          fill="none"
          stroke="var(--accent)"
          strokeWidth="1.5"
          strokeDasharray="3 3"
        />

        <ellipse
          cx="80"
          cy="282"
          rx="22"
          ry="8"
          fill="var(--paper)"
          stroke="var(--ink)"
          strokeWidth="1.5"
        />
        <path
          d="M60 282 Q 80 274 100 282"
          stroke="var(--ink)"
          strokeWidth="1.5"
          fill="none"
        />
        <text x="50" y="300" fontFamily="Pretendard" fontSize="10" fill="var(--accent-soft)">
          밥 주기
        </text>

        <rect
          x="250"
          y="260"
          width="100"
          height="30"
          rx="14"
          fill="var(--paper)"
          stroke="var(--ink)"
          strokeWidth="1.5"
        />
        <text x="285" y="310" fontFamily="Pretendard" fontSize="10" fill="var(--accent-soft)">
          방석
        </text>
      </svg>

      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '47.2%',
          transform: 'translateX(-50%)',
        }}
      >
        <div
          style={{
            background: 'var(--paper)',
            border: '1.5px solid var(--ink)',
            borderRadius: 16,
            padding: 8,
          }}
        >
          <CatSketch size={110} mood="wink" />
        </div>
        <div
          style={{
            fontFamily: 'Pretendard',
            fontWeight: 700,
            fontSize: 18,
            textAlign: 'center',
            marginTop: 6,
            color: 'var(--paper)',
          }}
        >
          "고마워 ♡"
        </div>
      </div>

      <div style={{ position: 'absolute', left: '8%', top: '55.6%' }}>
        <span className="chip" style={{ background: 'var(--paper)', color: 'var(--ink)' }}>
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
      <div className="chip" style={{ background: 'var(--paper)', color: 'var(--ink)' }}>
        {state.character.name || '이음이'} · Lv.{state.level}
      </div>
      <div style={{ display: 'flex', gap: 6 }}>
        <span className="chip" style={{ background: 'var(--paper)', color: 'var(--ink)' }}>
          ◉ {state.points}
        </span>
        <span className="chip" style={{ background: 'var(--paper)', color: 'var(--ink)' }}>
          ♡ {Math.round(intimacy / 10)}/10
        </span>
      </div>
    </div>

    <div style={{ marginTop: 408, marginLeft: 18, marginRight: 18 }}>
      <div
        className="hbox"
        style={{ padding: 14, background: 'var(--paper)', color: 'var(--ink)' }}
      >
        <h1 className="h-label">친밀도 &amp; 컨디션</h1>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 10 }}>
          {(
            [
              ['친밀도', `${intimacy}%`, 'var(--night)'],
              ['배부름', `${satiety}%`, 'var(--accent-2)'],
              ['활력', `${vitality}%`, 'var(--accent)'],
            ] as [string, string, string][]
          ).map(([n, p, c], i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontFamily: 'Pretendard', fontSize: 12, width: 48 }}>{n}</span>
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
            ['🍖', '먹이주기', () => { setSatiety((s) => Math.min(100, s + 15)); flash('냠냠 🐟 배부름 +15'); }],
            ['👕', '옷장', () => nav.go('inventory')],
            ['◐', '놀이', () => { setVitality((v) => Math.min(100, v + 10)); flash('꺄르륵! 활력 +10 ✦'); }],
            ['◰', '방꾸미기', () => nav.go('inventory')],
          ] as [string, string, () => void][]
        ).map(([ic, t, onAct], i) => (
          <button
            key={i}
            type="button"
            className="hbox"
            onClick={onAct}
            style={{
              padding: '12px 6px',
              textAlign: 'center',
              background: 'var(--paper)',
              color: 'var(--ink)',
              cursor: 'pointer',
              fontFamily: 'inherit',
            }}
          >
            <div style={{ fontSize: 22 }}>{ic}</div>
            <div className="tiny" style={{ marginTop: 4 }}>
              {t}
            </div>
          </button>
        ))}
      </div>

      <div
        className="hbox"
        style={{ marginTop: 10, padding: '12px 16px', background: 'var(--cream)', color: 'var(--ink)' }}
      >
        <div className="tiny" style={{ color: 'var(--ink)' }}>
          tip — 회고를 많이 할수록 이음이와 친밀도가 높아져요
        </div>
      </div>
    </div>
    </div>
    </div>
    {toast && <div className="toast" role="status">{toast}</div>}
    <TabBar active="cat" />
  </div>
  );
};

export const S19_Inventory = () => {
  const nav = useNav();
  const { state, dispatch } = useStore();
  const [sel, setSel] = useState<string | null>(state.equippedItem);
  const { toast, flash } = useToast();
  return (
  <div className="screen">
    <div className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 18px calc(140px + var(--safe-b, 0px))' }}>
    <div className="stage-body">
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <BackButton onClick={() => nav.back()} tone="var(--ink)" />
        <h1 className="h-title">인벤토리 / 옷장</h1>
      </div>
      <div className="h-label" style={{ marginTop: 4 }}>
        모은 아이템 · {state.unlockedItems.length}개 · {state.points} 포인트
      </div>

      <div style={{ display: 'flex', gap: 6, marginTop: 12, flexWrap: 'wrap' }}>
        {['전체', '👕 옷', '🎩 모자', '🍖 먹이', '◰ 방', '🎁 보상'].map((t, i) => (
          <span key={i} className={'chip ' + (i === 1 ? 'solid' : '')}>
            {t}
          </span>
        ))}
      </div>

      <div className="hbox" style={{ padding: 12, marginTop: 12 }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(96px, 1fr))',
            gap: 10,
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
          ).map(([n, sub, have], i) => (
            <div
              key={i}
              onClick={have ? () => setSel(n) : undefined}
              className="hbox dashed"
              style={{
                padding: 10,
                position: 'relative',
                background: have ? 'var(--paper)' : 'var(--paper-2)',
                opacity: have ? 1 : 0.6,
                cursor: have ? 'pointer' : 'default',
                outline: sel === n ? '1.5px solid var(--accent)' : 'none',
                outlineOffset: 1,
              }}
            >
              <ImgPh h={64} label={have ? '아이템' : '잠금'} />
              <div
                style={{
                  fontFamily: 'Pretendard',
                  fontWeight: 700,
                  fontSize: 13,
                  marginTop: 8,
                  textAlign: 'center',
                }}
              >
                {n}
              </div>
              <div className="tiny" style={{ textAlign: 'center' }}>{sub}</div>
              {state.equippedItem === n && (
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

      <h2 className="h-label" style={{ marginTop: 16, marginBottom: 8 }}>
        먹이 · 7개
      </h2>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(84px, 1fr))',
          gap: 8,
        }}
      >
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
            style={{ padding: 10, textAlign: 'center' }}
          >
            <div style={{ fontSize: 22 }}>{n.split(' ')[0]}</div>
            <div className="tiny" style={{ marginTop: 2 }}>{n.split(' ').slice(1).join(' ')}</div>
            <div style={{ fontFamily: 'Pretendard', fontWeight: 700, fontSize: 13, marginTop: 2 }}>
              × {c}
            </div>
          </div>
        ))}
      </div>
    </div>
    </div>
    <div
      className="pin-bottom"
      style={{
        bottom: 'calc(var(--tabbar-h, 64px) + 14px)',
        paddingInline: 'max(18px, calc((100% - var(--stage-max, 560px)) / 2))',
      }}
    >
      <button
        type="button"
        onClick={() => {
          if (sel) {
            dispatch({ type: 'item/equip', item: sel });
            flash(`${sel} 입었어요 ✓`);
          } else {
            flash('아이템을 먼저 선택해 주세요');
          }
        }}
        className="btn primary block"
        style={{ cursor: 'pointer', fontFamily: 'inherit' }}
      >
        {sel ? `${sel} 입히기` : '선택 입히기'}
      </button>
    </div>
    {toast && <div className="toast" role="status">{toast}</div>}
    <TabBar active="cat" />
  </div>
  );
};

export const S20_Report = () => {
  const nav = useNav();
  const { state } = useStore();
  const { toast, flash } = useToast();
  const weekCount = state.diaries.filter((e) => isWithinLastWeek(e)).length;
  const recent = latestEntry(state.diaries);
  const moodCell = recent ? recent.moods[0] : '🌙';
  const moodLabel = recent ? MOOD_LABEL[recent.moods[0]] : '기록 전';
  return (
  <div className="screen">
    <div className="screen-scroll" style={{ padding: 'calc(46px + var(--safe-t)) 18px calc(88px + var(--safe-b, 0px))' }}>
    <div className="stage-body">
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <BackButton onClick={() => nav.back()} tone="var(--pencil)" />
        <div className="h-label">주간 리포트 — 매주 월요일</div>
      </div>
      <h1 className="h-display" style={{ marginTop: 8, fontSize: 28 }}>
        5월 4째주
        <br />
        너의 일주일.
      </h1>
      <div className="h-label" style={{ marginTop: 6 }}>
        5/19 — 5/25 · 6일 기록 · 1일 휴식
      </div>

      <div
        className="hbox"
        style={{ padding: 14, marginTop: 14, background: 'var(--cream)' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <CatSketch size={64} mood="happy" />
          <div>
            <div className="tiny">한 줄 요약</div>
            <div
              style={{
                fontFamily: 'Pretendard',
                fontWeight: 700,
                fontSize: 18,
                marginTop: 4,
                color: 'var(--ink-soft)',
              }}
            >
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
            ['일기', `${weekCount}`, '회'],
            ['평균 수면', '6.4', '시간'],
            ['이번 주 감정', moodCell, moodLabel],
            ['포인트', `${state.points}`, '◉'],
            ['스트릭', `${state.streak}`, '일'],
            ['새 아이템', `${state.unlockedItems.length}`, '개'],
          ] as [string, string, string][]
        ).map(([t, n, u], i) => (
          <div
            key={i}
            className="hbox"
            style={{ padding: '12px 8px', textAlign: 'center' }}
          >
            <div className="tiny">{t}</div>
            <div
              style={{
                fontFamily: 'Pretendard',
                fontWeight: 700,
                fontSize: 24,
                marginTop: 4,
              }}
            >
              {n}
            </div>
            <div className="tiny" style={{ marginTop: 2 }}>{u}</div>
          </div>
        ))}
      </div>

      <div className="hbox" style={{ padding: 14, marginTop: 12 }}>
        <div className="tiny">이번 주 이야기</div>
        <div className="body" style={{ marginTop: 8, lineHeight: 1.6 }}>
          월·화에 회의가 길어 피곤이 컸어요.
          <br />
          수요일에 산책을 다시 시작한 뒤로
          <br />
          평온함이 늘었어요. 같은 패턴을 이어가요.
        </div>
      </div>

      <div
        className="hbox night"
        onClick={() => flash('🖼 리포트 카드 이미지 저장은 곧 지원돼요')}
        style={{
          padding: 12,
          marginTop: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          cursor: 'pointer',
        }}
      >
        <div className="ph-circle" style={{ width: 36, height: 36, background: 'var(--paper)' }}>
          ◇
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: 'Pretendard', fontWeight: 500, color: 'var(--paper)' }}>
            리포트 카드 저장
          </div>
          <div className="tiny" style={{ color: 'var(--accent-soft)' }}>
            이미지로 내보내기
          </div>
        </div>
        <span style={{ fontFamily: 'Pretendard', fontSize: 22, color: 'var(--paper)' }}>›</span>
      </div>
    </div>
    </div>
    {toast && <div className="toast" role="status">{toast}</div>}
    <TabBar active="ins" />
  </div>
  );
};
