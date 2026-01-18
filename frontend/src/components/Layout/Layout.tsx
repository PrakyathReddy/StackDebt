import React from 'react';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gray-900 text-green-400 font-mono">
      {/* Terminal-style background pattern */}
      <div className="absolute inset-0 opacity-5">
        <div className="h-full w-full" style={{
          backgroundImage: `repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(0, 255, 0, 0.1) 2px,
            rgba(0, 255, 0, 0.1) 4px
          )`
        }} />
      </div>
      
      {/* Main content */}
      <div className="relative z-10">
        <header className="border-b border-green-400/20 bg-gray-900/90 backdrop-blur-sm">
          <div className="container mx-auto px-4 py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="text-2xl font-bold text-terminal-green">
                  <span className="text-terminal-amber">$</span> StackDebt
                </div>
                <div className="hidden md:block text-sm text-gray-400">
                  Carbon Dating for Software Infrastructure
                </div>
              </div>
              
              {/* Terminal-style status indicator */}
              <div className="flex items-center space-x-2 text-xs">
                <div className="flex items-center space-x-1">
                  <div className="w-2 h-2 bg-terminal-green rounded-full animate-pulse"></div>
                  <span className="text-gray-400">ONLINE</span>
                </div>
              </div>
            </div>
          </div>
        </header>

        <main className="container mx-auto px-4 py-8">
          {children}
        </main>

        <footer className="border-t border-green-400/20 bg-gray-900/90 backdrop-blur-sm mt-16">
          <div className="container mx-auto px-4 py-6">
            <div className="flex items-center justify-between text-sm text-gray-400">
              <div>
                <span className="text-terminal-amber">stackdebt@analyzer:~$</span> 
                <span className="ml-2">Analyzing infrastructure since 2024</span>
              </div>
              <div className="hidden md:block">
                <span>Powered by Carbon Dating Algorithm v1.0</span>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default Layout;