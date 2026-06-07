import { Fragment, ReactNode, useEffect, useState } from 'react';
import { DCArtboard, DCSection, DesignCanvas } from './components/DesignCanvas';
import { TweaksPanel } from './components/TweaksPanel';
import { AppShell } from './components/AppShell';
import { C00_Cover, C01_System, C02_Flow } from './screens/cover';
import {
  S01_Splash,
  S02_Welcome,
  S03_Privacy,
  S04_CreateCat,
  S05_FirstMeet,
} from './screens/onboarding';
import {
  S06_HomeDay,
  S07_HomeNight,
  S08_DailyCheck,
  S09_AIChat,
} from './screens/home-day';
import {
  S10_RecapStart,
  S11_ChatDiary,
  S12_MoodFinalize,
  S13_Reward,
} from './screens/evening';
import {
  S14_Calendar,
  S15_DiaryDetail,
  S16_Stats,
  S17_Insights,
} from './screens/records';
import { S18_CatRoom, S19_Inventory, S20_Report } from './screens/character';
import { NavContext } from './lib/router';

// Two modes — design canvas (all 23 artboards) and app preview (interactive
// phone shell). Default is app preview; #design switches to the static canvas.

// Stub NavContext provider used for the design-canvas thumbnails — screens
// reference useNav() but the canvas is non-interactive, so clicks are no-ops.
const DesignNavStub = ({ children }: { children: ReactNode }) => (
  <NavContext.Provider
    value={{ go: () => undefined, back: () => undefined, reset: () => undefined, current: 'splash', night: true }}
  >
    {children}
  </NavContext.Provider>
);

const phone = (label: string, id: string, primary: string, note: string, child: ReactNode) => (
  <DCArtboard
    id={id}
    label={label}
    width={375}
    height={812}
    caption={
      <Fragment>
        <div>{primary}</div>
        <div className="note">{note}</div>
      </Fragment>
    }
  >
    {child}
  </DCArtboard>
);

const DesignMode = () => (
  <DesignNavStub>
    <DesignCanvas>
      <DCSection
        id="cover"
        title="00 · 컨셉 & 시스템"
        subtitle="기존 와이어프레임 분석 후 — 시간대 기반 캐릭터로 재설계"
      >
        <DCArtboard id="cover" label="Cover" width={900} height={720}>
          <C00_Cover />
        </DCArtboard>
        <DCArtboard id="system" label="디자인 시스템" width={900} height={720}>
          <C01_System />
        </DCArtboard>
        <DCArtboard id="flow" label="기능 순서 (Flow)" width={900} height={720}>
          <C02_Flow />
        </DCArtboard>
      </DCSection>

      <DCSection
        id="onboarding"
        title="01 · 온보딩 플로우"
        subtitle="첫 실행 → 5단계 시퀀스 (5분 이내)"
      >
        {phone('01 · Splash', '01', '앱 진입 · 캐릭터 컨셉(밤에 깨어남) 첫 노출. 자동 진행 1.5s.', '★ 밤 하늘 + 깨어난 이음이 — 컨셉을 첫 1.5초에 전달', <S01_Splash />)}
        {phone('02 · Welcome', '02', '1인 가구 가치 제안. [시작하기] 탭 → 03으로.', '★ 온보딩 첫인상 — status bar에서 시간대(아침)임을 암시', <S02_Welcome />)}
        {phone('03 · Privacy', '03', '로컬 우선 저장·익명 분석·언제든 삭제 — 신뢰 약속.', '★ 일기 = 가장 사적인 데이터 — 신뢰를 먼저 약속하고 시작', <S03_Privacy />)}
        {phone('04 · 캐릭터 생성', '04', '이름·털색·성격 선택. 성격은 말투에 영향.', '★ 캐릭터 = 내 분신 — 작은 커스텀이 큰 애착으로', <S04_CreateCat />)}
        {phone('05 · 첫 만남 (밤)', '05', '이음이 첫 대사 — 밤 모드 컨셉을 첫 화면에서 학습.', '★ 컨셉 — 밤에만 깨어나는 캐릭터를 첫 화면부터 학습시킴', <S05_FirstMeet />)}
      </DCSection>

      <DCSection
        id="home-day"
        title="02 · [홈 — 낮] 진입 후 흐름"
        subtitle="고양이는 자는 중 · AI 비서가 보조 (낮 모드)"
      >
        {phone('06 · 홈 (낮)', '06', '센터 [홈] 탭 진입 — 낮엔 이음이 수면. 데일리 체크 + AI 비서 진입점.', '★ 낮 모드 — 고양이 자는 중, 회고 CTA 없음. 데일리 체크가 메인', <S06_HomeDay />)}
        {phone('08 · 데일리 체크', '08', '홈 카드 탭 → 식사·수면·운동·물·햇볕 5체크. 회고 자동 메모.', '★ 5개 = 부담 적게, 점수보다 흔적', <S08_DailyCheck />)}
        {phone('09 · AI 비서 챗', '09', '홈 카드 탭 → 낮 자유 대화. 답변은 밤 회고로 자동 인계.', '★ 낮은 AI 비서 / 밤은 캐릭터 회고 — 톤이 다름', <S09_AIChat />)}
      </DCSection>

      <DCSection
        id="home-night"
        title="03 · [홈 — 밤] 회고 메인 흐름 ★"
        subtitle="앱의 심장 — 깨어난 이음이가 같이 정리"
      >
        {phone('07 · 홈 (밤)', '07', '저녁 시간대 자동 전환. 회고 CTA가 hero — 깨어난 이음이가 부른다.', '★ 밤 모드 — 회고 CTA가 hero, 깨어난 캐릭터가 부른다', <S07_HomeNight />)}
        {phone('10 · 회고 시작', '10', '[시작하기] → 낮 메모 인계 + 모드 선택(챗/짧게/보이스).', '★ NEW — 낮 동안 적어둔 메모가 회고를 더 똑똑하게', <S10_RecapStart />)}
        {phone('11 · ChatDiary (5턴)', '11', '이음이와 5턴 대화. AI가 행동 제안으로 마무리.', '★ AI가 회고를 "행동 제안"으로 마무리 — 챗봇 ≠ 일기', <S11_ChatDiary />)}
        {phone('12 · 감정 분석 · 일기', '12', '5턴 결과 → 감정 분포 + AI 일기 초안 + 내일 한 가지.', '★ 감정 분석 + AI 일기 초안 + 내일 1가지 — 한 화면에 통합', <S12_MoodFinalize />)}
        {phone('13 · 보상 모달', '13', '저장 직후 — 포인트/스트릭/새 아이템. 키우기로 자연 유도.', '★ 회고 → 즉시 보상 → 키우기로 자연스러운 동선', <S13_Reward />)}
      </DCSection>

      <DCSection
        id="calendar"
        title="04 · [달력 탭] 진입 후 흐름"
        subtitle="감정의 흐름을 한 눈에 — 회상 모드"
      >
        {phone('14 · 달력', '14', '좌측 [달력] 탭 → 월별 이모지 캘린더. 셀 탭 → 일기 디테일.', '★ 이모지 셀 = 감정 / 빈 동그라미 = 기록 없음', <S14_Calendar />)}
        {phone('15 · 일기 디테일', '15', '감정 분포·일기 본문·키워드·그날의 체크·내일 한 가지 이행 여부.', '★ 일기 = 회고 결과의 영구 보관 페이지', <S15_DiaryDetail />)}
      </DCSection>

      <DCSection
        id="stats"
        title="05 · [통계·인사이트 탭]"
        subtitle="기록의 모양 → AI 패턴 → 행동 제안"
      >
        {phone('16 · 통계', '16', '[통계] 탭 → 주/월 KPI · 요일별 작성 · 감정 분포 · 라이프스타일.', '★ D30 북극성 — 주 3회 이상 작성 60%', <S16_Stats />)}
        {phone('17 · 인사이트', '17', '[인사이트] 탭 → AI가 찾은 이번 주 패턴 → 추천 루틴 → 알람 추가.', '★ 패턴 → 행동 제안 → 알람화 — 인사이트가 "행동"으로', <S17_Insights />)}
      </DCSection>

      <DCSection
        id="character"
        title="06 · [키우기 탭] 진입 후 흐름"
        subtitle="회고 보상의 시각화 — 방·옷·먹이·리포트"
      >
        {phone('18 · 이음이 방 (밤)', '18', '[키우기] 탭 → 친밀도/배부름/활력 + 먹이주기·옷장·놀이·방꾸미기 4액션.', '★ 키우기 = 회고 보상의 시각화 — 방·옷·먹이', <S18_CatRoom />)}
        {phone('19 · 인벤토리 · 옷장', '19', '모은 아이템·먹이·잠금 보상. 잠금 = 다음 회고 동기.', '★ 잠금 아이템 = 다음 회고 동기 / "입는중" = 현재 적용', <S19_Inventory />)}
        {phone('20 · 주간 리포트', '20', '매주 월요일 푸시 — 한 줄 요약 + 숫자 그리드 + 이번 주 이야기 + 카드 저장.', '★ 주간 리포트 = 시리얼 컨텐츠 · 매주 월요일 푸시로 재방문', <S20_Report />)}
      </DCSection>
    </DesignCanvas>
    <TweaksPanel />
  </DesignNavStub>
);

export const App = () => {
  const [mode, setMode] = useState<'design' | 'app'>(() =>
    window.location.hash === '#design' ? 'design' : 'app',
  );

  useEffect(() => {
    const onHash = () =>
      setMode(window.location.hash === '#design' ? 'design' : 'app');
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  if (mode === 'design') {
    return <DesignMode />;
  }
  return (
    <AppShell
      onExitToDesign={() => {
        window.location.hash = 'design';
      }}
    />
  );
};
