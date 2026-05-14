import { Home, Calendar as CalendarIcon, BarChart3, Lightbulb, Package } from 'lucide-react';

interface BottomNavProps {
  currentPage: string;
  onNavigate: (page: string) => void;
}

export function BottomNav({ currentPage, onNavigate }: BottomNavProps) {
  const navItems = [
    { id: 'home', label: '홈', icon: Home },
    { id: 'calendar', label: '캘린더', icon: CalendarIcon },
    { id: 'statistics', label: '통계', icon: BarChart3 },
    { id: 'insights', label: '인사이트', icon: Lightbulb },
    { id: 'inventory', label: '키우기', icon: Package },
  ];

  return (
    <nav className="absolute bottom-0 left-0 right-0 h-24 md:h-28 bg-white/95 backdrop-blur-3xl border-t-2 border-[#E5DDD3] flex justify-around items-center px-6 md:px-8 rounded-b-[3rem] z-40 shadow-[0_-4px_20px_rgba(44,36,25,0.04)] pb-6">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = currentPage === item.id;
        
        return (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            className={`relative p-4 transition-all duration-500 rounded-[1.5rem] group ${
              isActive 
                ? 'bg-gradient-to-br from-[#2C2419] to-[#3D332A] shadow-[0_4px_16px_rgba(44,36,25,0.3)] scale-110' 
                : 'hover:bg-[#F7F3EE]'
            }`}
          >
            <Icon 
              size={22} 
              strokeWidth={isActive ? 2.5 : 2} 
              className={`transition-colors ${
                isActive ? 'text-[#F7F3EE]' : 'text-[#8B7A6A] group-hover:text-[#5A4A3A]'
              }`}
            />
            
            {/* 활성 인디케이터 */}
            {isActive && (
              <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-1 h-1 bg-[#D4A574] rounded-full"></div>
            )}
          </button>
        );
      })}
    </nav>
  );
}