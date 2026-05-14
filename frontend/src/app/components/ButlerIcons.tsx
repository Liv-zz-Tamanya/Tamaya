// 바텐더 고양이 집사 일러스트레이션 컴포넌트

interface IconProps {
  className?: string;
  size?: number;
}

// 고양이 집사 캐릭터 - 메인
export function ButlerCatIcon({ className = '', size = 64 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* 귀 */}
      <path
        d="M15 18 L10 8 L20 12 Z"
        fill="#A47C4B"
        stroke="#8B6239"
        strokeWidth="1.5"
      />
      <path
        d="M49 18 L54 8 L44 12 Z"
        fill="#A47C4B"
        stroke="#8B6239"
        strokeWidth="1.5"
      />
      
      {/* 얼굴 */}
      <circle cx="32" cy="32" r="20" fill="#C4966D" />
      <circle cx="32" cy="32" r="20" fill="url(#catGradient)" />
      
      {/* 눈 */}
      <ellipse cx="24" cy="28" rx="2.5" ry="4" fill="#2C2419" />
      <ellipse cx="40" cy="28" rx="2.5" ry="4" fill="#2C2419" />
      <circle cx="24.5" cy="27" r="1" fill="white" opacity="0.8" />
      <circle cx="40.5" cy="27" r="1" fill="white" opacity="0.8" />
      
      {/* 코 */}
      <path
        d="M32 34 L30 36 L34 36 Z"
        fill="#7B4B5A"
      />
      
      {/* 수염 */}
      <line x1="18" y1="32" x2="10" y2="30" stroke="#2C2419" strokeWidth="1" opacity="0.4" />
      <line x1="18" y1="35" x2="10" y2="36" stroke="#2C2419" strokeWidth="1" opacity="0.4" />
      <line x1="46" y1="32" x2="54" y2="30" stroke="#2C2419" strokeWidth="1" opacity="0.4" />
      <line x1="46" y1="35" x2="54" y2="36" stroke="#2C2419" strokeWidth="1" opacity="0.4" />
      
      {/* 볼 */}
      <circle cx="20" cy="36" r="3" fill="#FFB4A0" opacity="0.4" />
      <circle cx="44" cy="36" r="3" fill="#FFB4A0" opacity="0.4" />
      
      {/* 나비 넥타이 */}
      <path
        d="M28 48 L24 50 L28 52 L32 50 Z"
        fill="#2C2419"
      />
      <path
        d="M36 48 L40 50 L36 52 L32 50 Z"
        fill="#2C2419"
      />
      <circle cx="32" cy="50" r="1.5" fill="#D4A574" />
      
      <defs>
        <linearGradient id="catGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#C4966D" />
          <stop offset="100%" stopColor="#A47C4B" />
        </linearGradient>
      </defs>
    </svg>
  );
}

// 와인 글라스 아이콘
export function WineGlassIcon({ className = '', size = 48 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* 글라스 볼 */}
      <path
        d="M14 8 Q12 14 12 18 Q12 25 24 28 Q36 25 36 18 Q36 14 34 8 Z"
        fill="url(#wineGradient)"
        stroke="#7B4B5A"
        strokeWidth="1.5"
      />
      
      {/* 와인 */}
      <path
        d="M15 10 Q13 14 13 17 Q13 22 24 24 Q35 22 35 17 Q35 14 33 10 Z"
        fill="#7B4B5A"
        opacity="0.6"
      />
      
      {/* 하이라이트 */}
      <ellipse cx="19" cy="12" rx="3" ry="4" fill="white" opacity="0.3" />
      
      {/* 줄기 */}
      <rect x="22.5" y="28" width="3" height="12" fill="#E5DDD3" stroke="#D4C4B4" strokeWidth="1" />
      
      {/* 베이스 */}
      <ellipse cx="24" cy="42" rx="8" ry="2" fill="#E5DDD3" stroke="#D4C4B4" strokeWidth="1" />
      
      <defs>
        <linearGradient id="wineGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#F7F3EE" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#E5DDD3" stopOpacity="0.9" />
        </linearGradient>
      </defs>
    </svg>
  );
}

// 깃펜 아이콘
export function QuillIcon({ className = '', size = 48 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* 펜촉 */}
      <path
        d="M8 40 L12 28 L20 12 Q24 8 28 10 L18 34 L8 40 Z"
        fill="url(#quillGradient)"
        stroke="#8B6239"
        strokeWidth="1.5"
      />
      
      {/* 깃털 디테일 */}
      <path d="M20 12 L18 20" stroke="#8B6239" strokeWidth="1" opacity="0.4" />
      <path d="M22 14 L20 22" stroke="#8B6239" strokeWidth="1" opacity="0.4" />
      <path d="M24 16 L22 24" stroke="#8B6239" strokeWidth="1" opacity="0.4" />
      
      {/* 잉크 포인트 */}
      <circle cx="10" cy="38" r="2" fill="#2C2419" opacity="0.6" />
      
      <defs>
        <linearGradient id="quillGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#D4A574" />
          <stop offset="100%" stopColor="#A47C4B" />
        </linearGradient>
      </defs>
    </svg>
  );
}

// 노트북/일기장 아이콘
export function DiaryBookIcon({ className = '', size = 48 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* 책 커버 */}
      <rect
        x="10"
        y="8"
        width="28"
        height="36"
        rx="2"
        fill="url(#bookGradient)"
        stroke="#8B6239"
        strokeWidth="1.5"
      />
      
      {/* 책등 */}
      <rect x="10" y="8" width="4" height="36" fill="#8B6239" opacity="0.3" />
      
      {/* 페이지 */}
      <line x1="18" y1="18" x2="34" y2="18" stroke="#2C2419" strokeWidth="1" opacity="0.2" />
      <line x1="18" y1="24" x2="34" y2="24" stroke="#2C2419" strokeWidth="1" opacity="0.2" />
      <line x1="18" y1="30" x2="30" y2="30" stroke="#2C2419" strokeWidth="1" opacity="0.2" />
      
      {/* 장식 */}
      <circle cx="24" cy="14" r="2" fill="#D4A574" />
      
      <defs>
        <linearGradient id="bookGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#C4966D" />
          <stop offset="100%" stopColor="#A47C4B" />
        </linearGradient>
      </defs>
    </svg>
  );
}

// 스타/포인트 아이콘
export function StarPointIcon({ className = '', size = 48 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* 외곽 별 */}
      <path
        d="M24 6 L28 18 L40 20 L32 28 L34 40 L24 34 L14 40 L16 28 L8 20 L20 18 Z"
        fill="url(#starGradient)"
        stroke="#C09860"
        strokeWidth="1.5"
      />
      
      {/* 내부 하이라이트 */}
      <path
        d="M24 12 L26 20 L34 22 L28 28 L29 36 L24 32 L19 36 L20 28 L14 22 L22 20 Z"
        fill="white"
        opacity="0.3"
      />
      
      {/* 반짝임 */}
      <circle cx="38" cy="12" r="2" fill="#D4A574" opacity="0.8" />
      <circle cx="12" cy="36" r="1.5" fill="#D4A574" opacity="0.6" />
      
      <defs>
        <linearGradient id="starGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#FFE4A3" />
          <stop offset="50%" stopColor="#D4A574" />
          <stop offset="100%" stopColor="#C09860" />
        </linearGradient>
      </defs>
    </svg>
  );
}

// 불꽃/연속 기록 아이콘
export function FireStreakIcon({ className = '', size = 48 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* 외부 불꽃 */}
      <path
        d="M24 8 Q20 12 20 18 Q20 22 22 26 Q18 24 16 28 Q14 32 16 36 Q18 42 24 44 Q30 42 32 36 Q34 32 32 28 Q30 24 26 26 Q28 22 28 18 Q28 12 24 8 Z"
        fill="url(#fireGradient)"
      />
      
      {/* 내부 불꽃 */}
      <path
        d="M24 16 Q22 18 22 22 Q22 26 24 28 Q26 26 26 22 Q26 18 24 16 Z"
        fill="#FFE4A3"
        opacity="0.8"
      />
      
      {/* 하이라이트 */}
      <ellipse cx="24" cy="20" rx="2" ry="4" fill="white" opacity="0.4" />
      
      <defs>
        <linearGradient id="fireGradient" x1="50%" y1="0%" x2="50%" y2="100%">
          <stop offset="0%" stopColor="#FFB84D" />
          <stop offset="50%" stopColor="#FF8C4D" />
          <stop offset="100%" stopColor="#D4704D" />
        </linearGradient>
      </defs>
    </svg>
  );
}

// 전구/팁 아이콘
export function LightBulbIcon({ className = '', size = 48 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* 전구 유리 */}
      <path
        d="M24 8 Q16 8 16 18 Q16 24 18 28 L18 32 L30 32 L30 28 Q32 24 32 18 Q32 8 24 8 Z"
        fill="url(#bulbGradient)"
        stroke="#D4C4B4"
        strokeWidth="1.5"
      />
      
      {/* 필라멘트 */}
      <path
        d="M22 16 Q24 14 26 16 Q24 18 22 16"
        stroke="#C09860"
        strokeWidth="2"
        fill="none"
      />
      
      {/* 베이스 */}
      <rect x="20" y="32" width="8" height="4" rx="1" fill="#8B7A6A" />
      <rect x="21" y="36" width="6" height="3" rx="1" fill="#5A4A3A" />
      
      {/* 빛 효과 */}
      <circle cx="24" cy="18" r="8" fill="#FFE4A3" opacity="0.2" />
      <circle cx="24" cy="18" r="12" fill="#FFE4A3" opacity="0.1" />
      
      {/* 하이라이트 */}
      <ellipse cx="20" cy="14" rx="3" ry="5" fill="white" opacity="0.5" />
      
      <defs>
        <linearGradient id="bulbGradient" x1="50%" y1="0%" x2="50%" y2="100%">
          <stop offset="0%" stopColor="#FFF9F3" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#F7F3EE" stopOpacity="0.7" />
        </linearGradient>
      </defs>
    </svg>
  );
}

// 체크마크 아이콘 (완료)
export function CheckBadgeIcon({ className = '', size = 48 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* 배경 원 */}
      <circle cx="24" cy="24" r="18" fill="url(#checkGradient)" />
      
      {/* 체크 마크 */}
      <path
        d="M16 24 L21 30 L33 16"
        stroke="white"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      
      {/* 외곽선 */}
      <circle cx="24" cy="24" r="18" stroke="#8B6239" strokeWidth="1.5" fill="none" />
      
      <defs>
        <linearGradient id="checkGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#A47C4B" />
          <stop offset="100%" stopColor="#C4966D" />
        </linearGradient>
      </defs>
    </svg>
  );
}

// 스파클/반짝임 아이콘
export function SparkleIcon({ className = '', size = 48 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* 큰 별 */}
      <path
        d="M24 8 L26 20 L38 22 L28 30 L30 42 L24 36 L18 42 L20 30 L10 22 L22 20 Z"
        fill="url(#sparkleGradient1)"
        stroke="#C09860"
        strokeWidth="1"
      />
      
      {/* 작은 별들 */}
      <path
        d="M38 12 L39 14 L41 15 L39 16 L38 18 L37 16 L35 15 L37 14 Z"
        fill="#D4A574"
      />
      <path
        d="M12 32 L13 34 L15 35 L13 36 L12 38 L11 36 L9 35 L11 34 Z"
        fill="#D4A574"
      />
      
      <defs>
        <linearGradient id="sparkleGradient1" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#FFE4A3" />
          <stop offset="100%" stopColor="#D4A574" />
        </linearGradient>
      </defs>
    </svg>
  );
}

// 고양이 집사 - 다양한 표정
export function ButlerCatHappy({ className = '', size = 64 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* 귀 */}
      <path d="M15 18 L10 8 L20 12 Z" fill="#A47C4B" stroke="#8B6239" strokeWidth="1.5" />
      <path d="M49 18 L54 8 L44 12 Z" fill="#A47C4B" stroke="#8B6239" strokeWidth="1.5" />
      
      {/* 얼굴 */}
      <circle cx="32" cy="32" r="20" fill="url(#catHappyGradient)" />
      
      {/* 눈 - 웃는 눈 */}
      <path d="M21 28 Q24 26 27 28" stroke="#2C2419" strokeWidth="2" strokeLinecap="round" fill="none" />
      <path d="M37 28 Q40 26 43 28" stroke="#2C2419" strokeWidth="2" strokeLinecap="round" fill="none" />
      
      {/* 코 */}
      <path d="M32 34 L30 36 L34 36 Z" fill="#7B4B5A" />
      
      {/* 입 - 미소 */}
      <path d="M28 38 Q32 41 36 38" stroke="#2C2419" strokeWidth="1.5" strokeLinecap="round" fill="none" />
      
      {/* 수염 */}
      <line x1="18" y1="32" x2="10" y2="30" stroke="#2C2419" strokeWidth="1" opacity="0.4" />
      <line x1="18" y1="35" x2="10" y2="36" stroke="#2C2419" strokeWidth="1" opacity="0.4" />
      <line x1="46" y1="32" x2="54" y2="30" stroke="#2C2419" strokeWidth="1" opacity="0.4" />
      <line x1="46" y1="35" x2="54" y2="36" stroke="#2C2419" strokeWidth="1" opacity="0.4" />
      
      {/* 볼 */}
      <circle cx="20" cy="36" r="3" fill="#FFB4A0" opacity="0.5" />
      <circle cx="44" cy="36" r="3" fill="#FFB4A0" opacity="0.5" />
      
      {/* 나비 넥타이 */}
      <path d="M28 48 L24 50 L28 52 L32 50 Z" fill="#2C2419" />
      <path d="M36 48 L40 50 L36 52 L32 50 Z" fill="#2C2419" />
      <circle cx="32" cy="50" r="1.5" fill="#D4A574" />
      
      <defs>
        <linearGradient id="catHappyGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#C4966D" />
          <stop offset="100%" stopColor="#A47C4B" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export function ButlerCatThinking({ className = '', size = 64 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* 귀 */}
      <path d="M15 18 L10 8 L20 12 Z" fill="#A47C4B" stroke="#8B6239" strokeWidth="1.5" />
      <path d="M49 18 L54 8 L44 12 Z" fill="#A47C4B" stroke="#8B6239" strokeWidth="1.5" />
      
      {/* 얼굴 */}
      <circle cx="32" cy="32" r="20" fill="url(#catThinkGradient)" />
      
      {/* 눈 - 생각하는 눈 */}
      <circle cx="24" cy="28" r="2" fill="#2C2419" />
      <circle cx="40" cy="28" r="2" fill="#2C2419" />
      <path d="M22 25 L26 25" stroke="#2C2419" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M38 25 L42 25" stroke="#2C2419" strokeWidth="1.5" strokeLinecap="round" />
      
      {/* 코 */}
      <path d="M32 34 L30 36 L34 36 Z" fill="#7B4B5A" />
      
      {/* 입 - 고민 */}
      <path d="M28 40 L36 40" stroke="#2C2419" strokeWidth="1.5" strokeLinecap="round" />
      
      {/* 수염 */}
      <line x1="18" y1="32" x2="10" y2="30" stroke="#2C2419" strokeWidth="1" opacity="0.4" />
      <line x1="46" y1="32" x2="54" y2="30" stroke="#2C2419" strokeWidth="1" opacity="0.4" />
      
      {/* 나비 넥타이 */}
      <path d="M28 48 L24 50 L28 52 L32 50 Z" fill="#2C2419" />
      <path d="M36 48 L40 50 L36 52 L32 50 Z" fill="#2C2419" />
      <circle cx="32" cy="50" r="1.5" fill="#D4A574" />
      
      <defs>
        <linearGradient id="catThinkGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#C4966D" />
          <stop offset="100%" stopColor="#A47C4B" />
        </linearGradient>
      </defs>
    </svg>
  );
}
