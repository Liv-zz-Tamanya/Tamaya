import { BackButton, CatSketch, TabBar, useToast } from '../components/primitives';
import { useNav } from '../lib/router';
import { MOOD_LABEL, isWithinLastWeek, latestEntry, useStore } from '../lib/store';
import { CAT_SURVEY_URL, openSurvey } from '../lib/surveys';

// 18 · Cat Survey(키우기 → 설문 대체) / 20 · Weekly Report
// 키우기(방·옷장) 기능은 설문으로 사용자 의견을 먼저 모으기로 결정 —
// 화면 전체를 출시 예정 + 설문 티저로 대체 (PM 설문 링크는 surveys.ts에 주입).

export const S18_CatSurvey = () => {
  const nav = useNav();
  const { state } = useStore();
  const { toast, flash } = useToast();
  const name = state.character.name || '이음이';

  const goSurvey = () => {
    if (!openSurvey(CAT_SURVEY_URL)) {
      flash('설문 링크를 준비 중이에요 — 조금만 기다려줘요 🐾');
    }
  };

  return (
  <div
    className="screen"
    style={{
      background: 'linear-gradient(180deg, var(--night) 0%, var(--night-2) 100%)',
      color: 'var(--paper)',
    }}
  >
    <div className="screen-scroll" style={{ padding: 'calc(52px + var(--safe-t)) 24px calc(96px + var(--safe-b, 0px))' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <BackButton onClick={() => nav.back()} tone="var(--accent-soft)" />
        <div className="h-section" style={{ color: 'var(--accent-soft)' }}>이음이 키우기</div>
      </div>

      <h1 className="h-display" style={{ marginTop: 14, fontSize: 30, color: 'var(--paper)', lineHeight: 1.2 }}>
        {name} 키우기,
        <br />
        같이 만들어요
      </h1>
      <div className="tiny" style={{ marginTop: 8, color: 'var(--accent-soft)' }}>
        옷장 · 방꾸미기 · 먹이주기 — 출시 준비 중
      </div>

      <div style={{ marginTop: 24, display: 'flex', justifyContent: 'center' }}>
        <div
          style={{
            background: 'var(--paper)',
            borderRadius: 16,
            padding: 16,
            border: '2px solid var(--ink)',
          }}
        >
          <CatSketch size={132} mood="happy" />
        </div>
      </div>

      <div
        className="hbox"
        style={{ background: 'var(--paper)', color: 'var(--ink)', padding: 14, marginTop: 22 }}
      >
        <div style={{ fontFamily: 'Pretendard', fontWeight: 700 }}>
          어떤 키우기를 원하는지 들려주세요
        </div>
        <div className="tiny" style={{ marginTop: 4, color: 'var(--pencil)' }}>
          짧은 설문(새 창)으로 의견을 남기면, {name}의 방을 만들 때 그대로 반영할게요.
        </div>
        <button
          type="button"
          onClick={goSurvey}
          className="btn primary block"
          style={{ marginTop: 12, cursor: 'pointer', fontFamily: 'inherit' }}
        >
          설문 참여하기 ↗
        </button>
      </div>

      <div className="tiny" style={{ marginTop: 12, textAlign: 'center', color: 'var(--accent-soft)' }}>
        지금은 밤 회고를 쌓을수록 {name}와 더 가까워져요 · 🔥 {state.streak}일
      </div>
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
