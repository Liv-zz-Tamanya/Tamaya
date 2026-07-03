import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import './styles/tokens.css';      // 디자인 토큰 SSOT (Figma interop) — 먼저 로드
import './styles/responsive.css';  // 반응형 reflow 파운데이션
import './styles/sketch.css';      // 컴포넌트 스타일 (토큰 참조)

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
