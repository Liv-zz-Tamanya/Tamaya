import eumiImage from 'figma:asset/436e1c74ca1087a6ae01c4f7a6cba2a0c870a0a0.png';

interface EumiCharacterProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  mood?: 'happy' | 'excited' | 'neutral';
  showShadow?: boolean;
  className?: string;
}

export function EumiCharacter({ 
  size = 'md', 
  mood = 'happy',
  showShadow = true,
  className = '' 
}: EumiCharacterProps) {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16',
    xl: 'w-24 h-24'
  };

  const animations = {
    happy: 'animate-bounce-slow',
    excited: 'animate-wiggle',
    neutral: ''
  };

  return (
    <div 
      className={`
        ${sizeClasses[size]} 
        ${animations[mood]} 
        ${showShadow ? 'drop-shadow-md' : ''} 
        ${className}
        flex items-center justify-center
      `}
    >
      <img 
        src={eumiImage} 
        alt="이음이" 
        className="w-full h-full object-contain"
      />
    </div>
  );
}
