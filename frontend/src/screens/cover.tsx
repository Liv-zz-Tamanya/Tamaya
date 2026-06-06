import { CatSketch, HandArrow } from '../components/primitives';

// 00 · Cover / System / Flow — Foundation cards (900×720)

export const C00_Cover = () => (
  <div
    style={{
      width: '100%',
      height: '100%',
      padding: 40,
      background: 'var(--paper)',
      boxSizing: 'border-box',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      position: 'relative',
    }}
  >
    <div>
      <div className="h-section">Tamaya · Wireframes v3</div>
      <div className="h-display" style={{ fontSize: 80, marginTop: 10, lineHeight: 0.95 }}>
        밤에 깨어나는
        <br />
        <span className="squiggle">고양이 집사</span>와
        <br />
        보내는 하루.
      </div>
      <div className="body" style={{ marginTop: 24, fontSize: 18, maxWidth: 560, lineHeight: 1.5 }}>
        1인 가구를 위한 라이프스타일 · 일기 · 감정 분석 앱.
        <br />
        낮엔 작은 비서가 챙기고, 밤이 되면 캐릭터가 깨어나
        <br />
        하루를 함께 정리해요. 모바일 우선 반응형 웹 — 추후 앱화.
      </div>
    </div>
    <div style={{ display: 'flex', gap: 24, alignItems: 'flex-end', position: 'relative' }}>
      <div>
        <CatSketch size={140} sleeping />
        <div className="handwriting" style={{ textAlign: 'center', marginTop: -4 }}>
          낮 — 자는 중
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', fontSize: 32 }}>
        <HandArrow length={80} />
      </div>
      <div>
        <CatSketch size={140} mood="wink" />
        <div className="handwriting" style={{ textAlign: 'center', marginTop: 4 }}>
          밤 — 회고 시작
        </div>
      </div>
    </div>
    <div style={{ position: 'absolute', bottom: 36, right: 40, textAlign: 'right' }}>
      <div className="tiny">손그림 와이어프레임 · 375×812 모바일 우선 · 반응형 웹</div>
      <div className="tiny">2026.05.27 / 20 screens · 3 system cards</div>
    </div>
  </div>
);

export const C01_System = () => (
  <div
    style={{
      width: '100%',
      height: '100%',
      padding: 32,
      background: 'var(--paper)',
      overflow: 'hidden',
      boxSizing: 'border-box',
    }}
  >
    <div className="h-section">디자인 시스템 — 손그림 로우파이</div>
    <div className="h-display" style={{ fontSize: 36, marginTop: 4 }}>
      흑백 + 포인트 1색.
    </div>

    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 24, marginTop: 18 }}>
      <div>
        <div className="h-label" style={{ marginBottom: 8 }}>
          컬러
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {(
            [
              ['Paper', '#f5e6cf', '라떼 크림 — 배경'],
              ['Ink', '#3a2414', '다크 에스프레소 — 본문'],
              ['Coffee Brown', '#8c4a1f', '포인트 1 (CTA / 강조)'],
              ['Espresso Night', '#2b1810', '밤 모드 배경'],
              ['Caramel', '#b8804a', '낮 모드 강조'],
              ['Cream', '#fff5e1', '일기 / 메모'],
            ] as [string, string, string][]
          ).map(([n, c, d], i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div
                className="ph-square"
                style={{ width: 26, height: 26, background: c, borderColor: '#3a2414' }}
              />
              <span style={{ fontFamily: 'Patrick Hand', fontSize: 13, width: 96 }}>{n}</span>
              <span className="tiny" style={{ width: 70 }}>
                {c}
              </span>
              <span className="tiny" style={{ flex: 1 }}>
                {d}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="h-label" style={{ marginBottom: 8 }}>
          타이포
        </div>
        <div className="hbox" style={{ padding: 12 }}>
          <div className="h-display" style={{ fontSize: 28 }}>
            Caveat — 헤드라인
          </div>
          <div className="handwriting">손글씨 톤 (캐릭터 대사)</div>
          <div style={{ fontFamily: 'Patrick Hand', fontSize: 14, marginTop: 4 }}>
            Patrick Hand — UI 라벨
          </div>
          <div style={{ fontFamily: 'Gaegu', fontSize: 14 }}>개구 — 한글 본문 (Gaegu)</div>
          <div className="tiny" style={{ marginTop: 4 }}>
            Tiny — 부가 정보 / 11px
          </div>
        </div>
      </div>

      <div>
        <div className="h-label" style={{ marginBottom: 8 }}>
          UI 프리미티브
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <div className="btn primary">버튼</div>
          <div className="btn">고스트</div>
          <span className="chip">chip</span>
          <span className="chip solid">solid</span>
          <span className="chip dashed">dashed</span>
          <div className="check on">✓</div>
          <div className="check sq">○</div>
          <div className="mood-blob">😌</div>
        </div>
        <div className="hbox r-l" style={{ padding: 10, marginTop: 8 }}>
          박스 (살짝 기운)
        </div>
        <div className="hbox dashed r-r" style={{ padding: 10, marginTop: 6 }}>
          박스 (점선)
        </div>
        <div className="sticky" style={{ marginTop: 8 }}>
          스티키 노트 (메모)
        </div>
      </div>

      <div>
        <div className="h-label" style={{ marginBottom: 8 }}>
          시간대 모드 (핵심)
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <div className="hbox day" style={{ flex: 1, padding: 12 }}>
            <div className="tiny">DAY</div>
            <div className="h-title" style={{ fontSize: 18, marginTop: 2 }}>
              고양이는
              <br />
              자는 중
            </div>
            <div style={{ marginTop: 6 }}>
              <CatSketch size={64} sleeping />
            </div>
            <div className="tiny" style={{ marginTop: 4 }}>
              AI 비서가 응답
            </div>
          </div>
          <div className="hbox night" style={{ flex: 1, padding: 12 }}>
            <div className="tiny" style={{ color: '#d8a777' }}>
              NIGHT
            </div>
            <div className="h-title" style={{ fontSize: 18, marginTop: 2, color: '#fff' }}>
              이음이가
              <br />
              깨어났어요
            </div>
            <div
              style={{
                marginTop: 6,
                background: '#f5e6cf',
                display: 'inline-block',
                borderRadius: 8,
                padding: 4,
              }}
            >
              <CatSketch size={56} mood="wink" />
            </div>
            <div className="tiny" style={{ marginTop: 4, color: '#d8a777' }}>
              회고 / 일기
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
);

export const C02_Flow = () => (
  <div
    style={{
      width: '100%',
      height: '100%',
      padding: 32,
      background: 'var(--paper)',
      overflow: 'hidden',
      boxSizing: 'border-box',
    }}
  >
    <div className="h-section">기능 순서 — Day → Night → Recap → Reward</div>
    <div className="h-display" style={{ fontSize: 32, marginTop: 4 }}>
      핵심 흐름
    </div>

    <div style={{ marginTop: 18, display: 'flex', flexDirection: 'column', gap: 14 }}>
      {(
        [
          ['1', '온보딩', 'Splash → Welcome → Privacy → 캐릭터 생성 → 첫 만남', '#f5e6cf'],
          [
            '2',
            '낮 — 비서 모드',
            '홈(자는 중) → 데일리 체크(식사·수면·운동·물·햇볕) → AI 비서 챗',
            '#ead0a6',
          ],
          [
            '3',
            '밤 — 회고 (핵심)',
            '홈(깨어남) → 저녁 회고 시작 → 5턴 챗 → 감정 분석 + 일기 → 보상',
            '#d8a777',
          ],
          [
            '4',
            '회상 / 분석',
            '달력 → 일기 디테일 → 통계 → 인사이트(AI 패턴)',
            '#f0d9b5',
          ],
          [
            '5',
            '키우기',
            '이음이 방 → 옷장/인벤토리 → 주간 리포트(월요일 푸시)',
            '#d9c69e',
          ],
        ] as [string, string, string, string][]
      ).map(([n, t, d, c], i) => (
        <div key={i} style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
          <div
            className="ph-circle"
            style={{
              width: 44,
              height: 44,
              flex: 'none',
              fontFamily: 'Caveat',
              fontSize: 22,
              fontWeight: 700,
              background: c,
            }}
          >
            {n}
          </div>
          <div style={{ flex: 1 }}>
            <div className="h-title" style={{ fontSize: 22 }}>
              {t}
            </div>
            <div className="body" style={{ marginTop: 2 }}>
              {d}
            </div>
          </div>
          <span style={{ fontFamily: 'Caveat', fontSize: 30, color: '#8c4a1f' }}>
            {i < 4 ? '↓' : '✓'}
          </span>
        </div>
      ))}
    </div>

    <div className="sticky" style={{ marginTop: 18, transform: 'rotate(-1deg)' }}>
      북극성: D30 기준 — 주 3회 이상 회고 작성 60%. 모든 화면이 이 한 가지 행동을 향함.
    </div>
  </div>
);
