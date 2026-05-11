import { useState } from 'react'
import { Sparkles, Zap, GraduationCap, Rocket, BarChart2, Users, BookOpen, Clock, Trophy, Flame, Target, Star, ArrowLeft, ShieldCheck, FileText, Settings, Bell, Search, LayoutDashboard, LogOut, Mail, MessageSquare, User, Lock, ArrowRight, Plus, Trash2, CheckCircle } from 'lucide-react'

function App() {
  const [view, setView] = useState<'landing' | 'teacher' | 'student' | 'contact' | 'login' | 'signup'>('landing')
  const [studentGrade, setStudentGrade] = useState(10) // Default to Class 10 (Mature)
  const [userRole, setUserRole] = useState<'teacher' | 'student'>('student')

  // Shared Header for Landing Page
  const LandingHeader = () => (
    <header className="p-6 flex justify-between items-center relative z-10">
      <div className="flex items-center gap-3 cursor-pointer" onClick={() => setView('landing')}>
        <div className="w-12 h-12 bg-cobalt rounded-xl border-[2px] border-ink flex items-center justify-center shadow-[3px_3px_0_0_#1A1A1A]">
          <Sparkles className="text-white" size={24} fill="white" />
        </div>
        <div>
          <h1 className="font-display font-black text-2xl tracking-tighter leading-none">Quizpop</h1>
          <p className="font-accent text-lg text-cobalt leading-none">make learning loud</p>
        </div>
      </div>
      
      <div className="flex items-center gap-3">
        <button 
          onClick={() => setView('contact')}
          className="bg-white font-display font-extrabold text-sm px-4 py-2 border-[2px] border-ink rounded-full shadow-[3px_3px_0_0_#1A1A1A] hover:translate-x-[-1px] hover:translate-y-[-1px] hover:shadow-[4px_4px_0_0_#1A1A1A] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all flex items-center gap-2 cursor-pointer"
        >
          <Zap size={16} fill="black" /> CONTACT
        </button>
        <button 
          onClick={() => setView('login')}
          className="bg-paper font-display font-extrabold text-sm px-4 py-2 border-[2px] border-ink rounded-full shadow-[3px_3px_0_0_#1A1A1A] hover:translate-x-[-1px] hover:translate-y-[-1px] hover:shadow-[4px_4px_0_0_#1A1A1A] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all cursor-pointer"
        >
          LOG IN
        </button>
        <button 
          onClick={() => setView('signup')}
          className="bg-lemon font-display font-extrabold text-sm px-4 py-2 border-[2px] border-ink rounded-full shadow-[3px_3px_0_0_#1A1A1A] hover:translate-x-[-1px] hover:translate-y-[-1px] hover:shadow-[4px_4px_0_0_#1A1A1A] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all cursor-pointer"
        >
          SIGN UP
        </button>
      </div>
    </header>
  )

  // Sidebar Component for Dashboards
  const Sidebar = ({ role, activeTab, setActiveTab }: { role: 'teacher' | 'student', activeTab: string, setActiveTab: (tab: string) => void }) => (
    <div className="w-64 bg-white border-r-[2px] border-ink flex flex-col p-6 justify-between h-screen sticky top-0">
      <div className="space-y-8">
        {/* Logo */}
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => setView('landing')}>
          <div className="w-10 h-10 bg-cobalt rounded-lg border-[2px] border-ink flex items-center justify-center shadow-[2px_2px_0_0_#1A1A1A]">
            <Sparkles className="text-white" size={20} fill="white" />
          </div>
          <div>
            <h1 className="font-display font-black text-xl tracking-tighter leading-none">Quizpop</h1>
            <p className="font-accent text-sm text-cobalt leading-none">portal</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-2">
          <div 
            onClick={() => setActiveTab('dashboard')}
            className={`p-2.5 font-bold text-sm flex items-center gap-3 cursor-pointer rounded-lg transition-colors border-[2px] ${activeTab === 'dashboard' ? 'bg-paper border-ink shadow-[2px_2px_0_0_#1A1A1A]' : 'border-transparent hover:bg-paper'}`}
          >
            <LayoutDashboard size={18} className={role === 'teacher' ? 'text-cobalt' : 'text-mint'} /> Dashboard
          </div>
          <div 
            onClick={() => setActiveTab('assessments')}
            className={`p-2.5 font-bold text-sm flex items-center gap-3 cursor-pointer rounded-lg transition-colors border-[2px] ${activeTab === 'assessments' ? 'bg-paper border-ink shadow-[2px_2px_0_0_#1A1A1A]' : 'border-transparent hover:bg-paper'}`}
          >
            <BookOpen size={18} /> {role === 'teacher' ? 'Assessments' : 'My Quests'}
          </div>
          <div 
            onClick={() => setActiveTab('community')}
            className={`p-2.5 font-bold text-sm flex items-center gap-3 cursor-pointer rounded-lg transition-colors border-[2px] ${activeTab === 'community' ? 'bg-paper border-ink shadow-[2px_2px_0_0_#1A1A1A]' : 'border-transparent hover:bg-paper'}`}
          >
            {role === 'teacher' ? <Users size={18} /> : <Trophy size={18} />} {role === 'teacher' ? 'Students' : 'Leaderboard'}
          </div>
          <div 
            onClick={() => setActiveTab('resources')}
            className={`p-2.5 font-bold text-sm flex items-center gap-3 cursor-pointer rounded-lg transition-colors border-[2px] ${activeTab === 'resources' ? 'bg-paper border-ink shadow-[2px_2px_0_0_#1A1A1A]' : 'border-transparent hover:bg-paper'}`}
          >
            <FileText size={18} /> Resources
          </div>
          <div 
            onClick={() => setActiveTab('settings')}
            className={`p-2.5 font-bold text-sm flex items-center gap-3 cursor-pointer rounded-lg transition-colors border-[2px] ${activeTab === 'settings' ? 'bg-paper border-ink shadow-[2px_2px_0_0_#1A1A1A]' : 'border-transparent hover:bg-paper'}`}
          >
            <Settings size={18} /> Settings
          </div>
        </nav>
      </div>

      {/* Bottom Profile/Logout */}
      <div className="border-t-[2px] border-ink pt-4 space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-lemon rounded-full border-[2px] border-ink flex items-center justify-center font-display font-black">
            {role === 'teacher' ? 'TR' : 'ST'}
          </div>
          <div>
            <p className="font-bold text-sm">{role === 'teacher' ? 'Prof. Sharma' : 'Alex M.'}</p>
            <p className="text-xs font-bold text-ink/50">{role === 'teacher' ? 'Mathematics' : 'Grade 10'}</p>
          </div>
        </div>
        <button 
          onClick={() => setView('landing')}
          className="w-full bg-paper font-display font-extrabold text-xs px-4 py-2 border-[2px] border-ink rounded-lg shadow-[2px_2px_0_0_#1A1A1A] hover:translate-x-[-1px] hover:translate-y-[-1px] hover:shadow-[3px_3px_0_0_#1A1A1A] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all flex items-center justify-center gap-2 cursor-pointer"
        >
          <LogOut size={14} /> Log Out to Portal
        </button>
      </div>
    </div>
  )

  // Landing Page
  const LandingView = () => (
    <>
      <LandingHeader />
      {/* Background Shapes */}
      <div className="absolute top-[120px] left-[-50px] w-40 h-40 bg-lemon rounded-full border-[3px] border-ink z-0"></div>
      <div className="absolute top-[350px] right-10 w-20 h-20 bg-mint border-[3px] border-ink z-0"></div>
      <div className="absolute top-[160px] right-[35%] text-tang text-4xl z-0">★</div>
      
      <main className="container mx-auto px-6 py-8 relative z-10">
        {/* Badge */}
        <div className="flex justify-center mb-6">
          <div className="bg-white border-[3px] border-ink px-5 py-1.5 rounded-full shadow-[4px_4px_0_0_#1A1A1A] font-display font-black text-xs uppercase tracking-wider flex items-center gap-2">
            ✦ ASSESSMENT ENGINE FOR BOLD CLASSROOMS
          </div>
        </div>

        {/* Heading */}
        <div className="text-center mb-4 relative">
          <h1 className="font-display font-black text-6xl md:text-8xl tracking-tighter leading-[0.9] flex flex-col items-center">
            <div className="flex items-center flex-wrap justify-center">
              Quizzes that 
              <span className="bg-lemon border-[3px] border-ink px-5 py-1 rounded-2xl shadow-[6px_6px_0_0_#1A1A1A] rotate-[-2deg] inline-block mx-3 my-2">pop.</span>
            </div>
            <div className="flex items-center flex-wrap justify-center">
              Learning that 
              <span className="bg-bubble border-[3px] border-ink px-5 py-1 rounded-2xl shadow-[6px_6px_0_0_#1A1A1A] rotate-[2deg] inline-block mx-3 my-2">sticks.</span>
            </div>
          </h1>
        </div>

        {/* Subtext */}
        <p className="font-accent text-3xl text-center text-ink mb-12">
          Pick your side. Are you here to teach, or to take it on?
        </p>

        {/* Cards Grid */}
        <div className="grid md:grid-cols-2 gap-10 max-w-6xl mx-auto mb-16">
          {/* Teach Card */}
          <div className="bg-cobalt border-[3px] border-ink rounded-3xl p-10 relative overflow-hidden shadow-[6px_6px_0_0_#1A1A1A] hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[8px_8px_0_0_#1A1A1A] hover:rotate-[-3deg] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-all duration-150 rotate-[-1deg]">
            <div className="absolute top-[-40px] right-[-40px] w-40 h-40 bg-lemon rounded-full border-[3px] border-ink flex items-end justify-start pb-10 pl-10">
              <GraduationCap size={36} className="text-ink" />
            </div>
            
            <p className="font-accent text-2xl text-lemon mb-1">I'm here to</p>
            <h2 className="font-display font-black text-7xl text-white mb-4">Teach</h2>
            <p className="text-white text-lg font-bold max-w-[75%] mb-10">
              Craft quirky assessments, track every learner, and grade with a grin. Bento-grid analytics included.
            </p>
            <button 
              onClick={() => { setUserRole('teacher'); setView('login'); }}
              className="bg-lemon text-ink font-display font-extrabold text-lg px-6 py-3 border-[3px] border-ink rounded-xl shadow-[4px_4px_0_0_#1A1A1A] hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[6px_6px_0_0_#1A1A1A] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-all cursor-pointer flex items-center gap-2"
            >
              Open Command Center 🚀
            </button>
          </div>

          {/* Quest Card */}
          <div className="bg-bubble border-[3px] border-ink rounded-3xl p-10 relative overflow-hidden shadow-[6px_6px_0_0_#1A1A1A] hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[8px_8px_0_0_#1A1A1A] hover:rotate-[3deg] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-all duration-150 rotate-[1deg]">
            <div className="absolute top-[-40px] left-[-40px] w-40 h-40 bg-mint rounded-full border-[3px] border-ink flex items-end justify-end pb-10 pr-10">
              <Rocket size={36} className="text-ink" />
            </div>
            
            <p className="font-accent text-2xl text-ink/70 mb-1 text-right">I'm here to</p>
            <h2 className="font-display font-black text-7xl text-ink mb-4 text-right">Quest</h2>
            <p className="text-ink text-lg font-bold text-right ml-auto max-w-[75%] mb-10">
              Take quizzes, build streaks, climb the leaderboard. Your XP is calling.
            </p>
            <div className="flex justify-end">
              <button 
                onClick={() => { setUserRole('student'); setView('login'); }}
                className="bg-mint text-ink font-display font-extrabold text-lg px-6 py-3 border-[3px] border-ink rounded-xl shadow-[4px_4px_0_0_#1A1A1A] hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[6px_6px_0_0_#1A1A1A] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-all cursor-pointer flex items-center gap-2"
              >
                <Zap size={18} fill="black" /> Enter Arena
              </button>
            </div>
          </div>
        </div>
      </main>
    </>
  )

  // Contact Page
  const ContactView = () => (
    <div className="min-h-screen bg-cream flex flex-col">
      <header className="p-6 flex justify-between items-center relative z-10">
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => setView('landing')}>
          <div className="w-12 h-12 bg-cobalt rounded-xl border-[2px] border-ink flex items-center justify-center shadow-[3px_3px_0_0_#1A1A1A]">
            <Sparkles className="text-white" size={24} fill="white" />
          </div>
          <div>
            <h1 className="font-display font-black text-2xl tracking-tighter leading-none">Quizpop</h1>
            <p className="font-accent text-lg text-cobalt leading-none">make learning loud</p>
          </div>
        </div>
        <button 
          onClick={() => setView('landing')}
          className="bg-white font-display font-extrabold text-sm px-4 py-2 border-[2px] border-ink rounded-full shadow-[3px_3px_0_0_#1A1A1A] hover:translate-x-[-1px] hover:translate-y-[-1px] hover:shadow-[4px_4px_0_0_#1A1A1A] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all flex items-center gap-2 cursor-pointer"
        >
          <ArrowLeft size={16} /> Back to Home
        </button>
      </header>

      <main className="container mx-auto px-6 py-8 flex-grow flex items-center justify-center">
        <div className="bg-white border-[3px] border-ink rounded-3xl p-8 max-w-2xl w-full shadow-[6px_6px_0_0_#1A1A1A] relative">
          <div className="absolute top-[-20px] right-[-20px] w-12 h-12 bg-lemon border-[2px] border-ink rounded-full flex items-center justify-center font-display font-black text-xl shadow-[2px_2px_0_0_#1A1A1A]">?</div>
          
          <h2 className="font-display font-black text-4xl mb-2 tracking-tight">Let's Connect!</h2>
          <p className="font-accent text-xl text-ink/70 mb-6">Want a live demo or have questions? Drop us a line.</p>

          <form className="space-y-5" onSubmit={(e) => e.preventDefault()}>
            <div>
              <label className="font-display font-bold text-sm block mb-1">Your Name</label>
              <div className="relative">
                <User size={18} className="absolute left-3 top-3 text-ink/40" />
                <input type="text" placeholder="Alex Murphy" className="w-full pl-10 pr-4 py-2.5 border-[2px] border-ink rounded-lg focus:outline-none focus:shadow-[3px_3px_0_0_#1A1A1A] transition-all" />
              </div>
            </div>
            <div>
              <label className="font-display font-bold text-sm block mb-1">School Email</label>
              <div className="relative">
                <Mail size={18} className="absolute left-3 top-3 text-ink/40" />
                <input type="email" placeholder="alex@school.edu" className="w-full pl-10 pr-4 py-2.5 border-[2px] border-ink rounded-lg focus:outline-none focus:shadow-[3px_3px_0_0_#1A1A1A] transition-all" />
              </div>
            </div>
            <div>
              <label className="font-display font-bold text-sm block mb-1">Message</label>
              <div className="relative">
                <MessageSquare size={18} className="absolute left-3 top-3 text-ink/40" />
                <textarea rows={4} placeholder="Tell us what you're looking for..." className="w-full pl-10 pr-4 py-2.5 border-[2px] border-ink rounded-lg focus:outline-none focus:shadow-[3px_3px_0_0_#1A1A1A] transition-all"></textarea>
              </div>
            </div>

            <div className="flex justify-center pt-2">
              <button className="bg-white font-display font-extrabold text-lg px-8 py-3 border-[3px] border-ink rounded-full shadow-[4px_4px_0_0_#1A1A1A] hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[6px_6px_0_0_#1A1A1A] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-all flex items-center gap-2 cursor-pointer">
                <Zap size={20} fill="black" /> CONTACT
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  )

  // Login Page
  const LoginView = () => (
    <div className="min-h-screen bg-cream flex flex-col">
      <header className="p-6 flex justify-between items-center relative z-10">
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => setView('landing')}>
          <div className="w-12 h-12 bg-cobalt rounded-xl border-[2px] border-ink flex items-center justify-center shadow-[3px_3px_0_0_#1A1A1A]">
            <Sparkles className="text-white" size={24} fill="white" />
          </div>
          <div>
            <h1 className="font-display font-black text-2xl tracking-tighter leading-none">Quizpop</h1>
            <p className="font-accent text-lg text-cobalt leading-none">make learning loud</p>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8 flex-grow flex items-center justify-center">
        <div className="bg-white border-[3px] border-ink rounded-3xl p-8 max-w-md w-full shadow-[6px_6px_0_0_#1A1A1A] relative">
          <h2 className="font-display font-black text-4xl mb-2 tracking-tight">Welcome Back</h2>
          <p className="font-accent text-xl text-ink/70 mb-6">Log in to continue your journey.</p>

          <form className="space-y-5" onSubmit={(e) => { e.preventDefault(); setView(userRole); }}>
            <div>
              <label className="font-display font-bold text-sm block mb-1">Email Address</label>
              <div className="relative">
                <Mail size={18} className="absolute left-3 top-3 text-ink/40" />
                <input type="email" placeholder="you@school.edu" className="w-full pl-10 pr-4 py-2.5 border-[2px] border-ink rounded-lg focus:outline-none focus:shadow-[3px_3px_0_0_#1A1A1A] transition-all" required />
              </div>
            </div>
            <div>
              <label className="font-display font-bold text-sm block mb-1">Password</label>
              <div className="relative">
                <Lock size={18} className="absolute left-3 top-3 text-ink/40" />
                <input type="password" placeholder="••••••••" className="w-full pl-10 pr-4 py-2.5 border-[2px] border-ink rounded-lg focus:outline-none focus:shadow-[3px_3px_0_0_#1A1A1A] transition-all" required />
              </div>
            </div>

            <button type="submit" className="w-full bg-cobalt text-white font-display font-extrabold text-lg px-6 py-3 border-[3px] border-ink rounded-xl shadow-[4px_4px_0_0_#1A1A1A] hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[6px_6px_0_0_#1A1A1A] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-all flex items-center justify-center gap-2 cursor-pointer">
              Log In <ArrowRight size={18} />
            </button>
          </form>

          <p className="text-center mt-6 text-sm font-bold">
            Don't have an account?{' '}
            <span onClick={() => setView('signup')} className="text-cobalt cursor-pointer border-b-2 border-cobalt">Sign up</span>
          </p>
        </div>
      </main>
    </div>
  )

  // Sign Up Page
  const SignupView = () => (
    <div className="min-h-screen bg-cream flex flex-col">
      <header className="p-6 flex justify-between items-center relative z-10">
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => setView('landing')}>
          <div className="w-12 h-12 bg-cobalt rounded-xl border-[2px] border-ink flex items-center justify-center shadow-[3px_3px_0_0_#1A1A1A]">
            <Sparkles className="text-white" size={24} fill="white" />
          </div>
          <div>
            <h1 className="font-display font-black text-2xl tracking-tighter leading-none">Quizpop</h1>
            <p className="font-accent text-lg text-cobalt leading-none">make learning loud</p>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8 flex-grow flex items-center justify-center">
        <div className="bg-white border-[3px] border-ink rounded-3xl p-8 max-w-md w-full shadow-[6px_6px_0_0_#1A1A1A] relative">
          <h2 className="font-display font-black text-4xl mb-2 tracking-tight">Join the Movement</h2>
          <p className="font-accent text-xl text-ink/70 mb-6">Create your account to get started.</p>

          <form className="space-y-5" onSubmit={(e) => { e.preventDefault(); setView(userRole); }}>
            <div>
              <label className="font-display font-bold text-sm block mb-1">Full Name</label>
              <div className="relative">
                <User size={18} className="absolute left-3 top-3 text-ink/40" />
                <input type="text" placeholder="Alex Murphy" className="w-full pl-10 pr-4 py-2.5 border-[2px] border-ink rounded-lg focus:outline-none focus:shadow-[3px_3px_0_0_#1A1A1A] transition-all" required />
              </div>
            </div>
            <div>
              <label className="font-display font-bold text-sm block mb-1">Email Address</label>
              <div className="relative">
                <Mail size={18} className="absolute left-3 top-3 text-ink/40" />
                <input type="email" placeholder="you@school.edu" className="w-full pl-10 pr-4 py-2.5 border-[2px] border-ink rounded-lg focus:outline-none focus:shadow-[3px_3px_0_0_#1A1A1A] transition-all" required />
              </div>
            </div>
            <div>
              <label className="font-display font-bold text-sm block mb-1">Password</label>
              <div className="relative">
                <Lock size={18} className="absolute left-3 top-3 text-ink/40" />
                <input type="password" placeholder="••••••••" className="w-full pl-10 pr-4 py-2.5 border-[2px] border-ink rounded-lg focus:outline-none focus:shadow-[3px_3px_0_0_#1A1A1A] transition-all" required />
              </div>
            </div>

            <div>
              <label className="font-display font-bold text-sm block mb-2">I am a...</label>
              <div className="grid grid-cols-2 gap-4">
                <div 
                  onClick={() => setUserRole('student')}
                  className={`border-[2px] border-ink rounded-lg p-3 text-center cursor-pointer font-bold text-sm transition-all ${userRole === 'student' ? 'bg-mint shadow-[2px_2px_0_0_#1A1A1A]' : 'bg-paper hover:bg-white'}`}
                >
                  Student
                </div>
                <div 
                  onClick={() => setUserRole('teacher')}
                  className={`border-[2px] border-ink rounded-lg p-3 text-center cursor-pointer font-bold text-sm transition-all ${userRole === 'teacher' ? 'bg-cobalt text-white shadow-[2px_2px_0_0_#1A1A1A]' : 'bg-paper hover:bg-white'}`}
                >
                  Teacher
                </div>
              </div>
            </div>

            <button type="submit" className="w-full bg-lemon text-ink font-display font-extrabold text-lg px-6 py-3 border-[3px] border-ink rounded-xl shadow-[4px_4px_0_0_#1A1A1A] hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[6px_6px_0_0_#1A1A1A] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none transition-all flex items-center justify-center gap-2 cursor-pointer">
              Sign Up <ArrowRight size={18} />
            </button>
          </form>

          <p className="text-center mt-6 text-sm font-bold">
            Already have an account?{' '}
            <span onClick={() => setView('login')} className="text-cobalt cursor-pointer border-b-2 border-cobalt">Log in</span>
          </p>
        </div>
      </main>
    </div>
  )

  // Teacher Dashboard View
  const TeacherView = () => {
    const [activeTab, setActiveTab] = useState('dashboard')
    const [isCreatingTest, setIsCreatingTest] = useState(false)
    const [testQuestions, setTestQuestions] = useState([{ question: '', options: ['', '', '', ''], correct: 0 }])

    return (
      <div className="min-h-screen bg-paper flex">
        <Sidebar role="teacher" activeTab={activeTab} setActiveTab={setActiveTab} />
        
        <div className="flex-grow flex flex-col">
          {/* Top Bar */}
          <div className="bg-white border-b-[2px] border-ink px-6 py-3 flex justify-between items-center">
            <div className="relative hidden sm:block">
              <Search size={16} className="absolute left-3 top-2.5 text-ink/40" />
              <input type="text" placeholder="Search data..." className="pl-10 pr-4 py-1.5 border-[2px] border-ink rounded-lg text-sm focus:outline-none focus:shadow-[2px_2px_0_0_#1A1A1A]" />
            </div>
            <div className="flex items-center gap-4">
              <button className="relative p-1.5 border-[2px] border-ink rounded-lg hover:bg-paper cursor-pointer">
                <Bell size={18} />
                <span className="absolute top-[-4px] right-[-4px] w-3 h-3 bg-bubble rounded-full border-[1px] border-ink"></span>
              </button>
              <button className="p-1.5 border-[2px] border-ink rounded-lg hover:bg-paper cursor-pointer">
                <Settings size={18} />
              </button>
            </div>
          </div>

          {/* Content Based on Tab */}
          <main className="p-6 flex-grow overflow-auto">
            {activeTab === 'dashboard' && (
              <>
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
                  <div>
                    <h2 className="font-display font-black text-3xl tracking-tight">Analytics Overview</h2>
                    <p className="text-sm font-bold text-ink/60">Class 10-A • Academic Year 2026</p>
                  </div>
                  <button 
                    onClick={() => { setActiveTab('assessments'); setIsCreatingTest(true); }}
                    className="bg-cobalt text-white font-display font-extrabold text-sm px-5 py-2.5 border-[2px] border-ink rounded-lg shadow-[3px_3px_0_0_#1A1A1A] hover:translate-x-[-1px] hover:translate-y-[-1px] hover:shadow-[4px_4px_0_0_#1A1A1A] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all flex items-center gap-2 cursor-pointer"
                  >
                     Generate New Assessment
                  </button>
                </div>

                {/* Stat Tiles */}
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-5 mb-6">
                  <div className="bg-white border-[2px] border-ink rounded-xl p-5 shadow-[3px_3px_0_0_#1A1A1A]">
                    <div className="flex justify-between items-center mb-3">
                      <p className="font-display font-bold text-xs uppercase tracking-wider text-ink/60">Total Students</p>
                      <Users className="text-cobalt" size={18} />
                    </div>
                    <div className="flex items-baseline gap-2">
                      <p className="font-display font-black text-4xl">124</p>
                      <span className="text-xs font-bold text-mint">+3 this month</span>
                    </div>
                  </div>
                  <div className="bg-white border-[2px] border-ink rounded-xl p-5 shadow-[3px_3px_0_0_#1A1A1A]">
                    <div className="flex justify-between items-center mb-3">
                      <p className="font-display font-bold text-xs uppercase tracking-wider text-ink/60">Active Tests</p>
                      <BookOpen className="text-mint" size={18} />
                    </div>
                    <div className="flex items-baseline gap-2">
                      <p className="font-display font-black text-4xl">4</p>
                      <span className="text-xs font-bold text-ink/60">Across 2 subjects</span>
                    </div>
                  </div>
                  <div className="bg-white border-[2px] border-ink rounded-xl p-5 shadow-[3px_3px_0_0_#1A1A1A]">
                    <div className="flex justify-between items-center mb-3">
                      <p className="font-display font-bold text-xs uppercase tracking-wider text-ink/60">Average Score</p>
                      <BarChart2 className="text-lemon" size={18} />
                    </div>
                    <div className="flex items-baseline gap-2">
                      <p className="font-display font-black text-4xl">78%</p>
                      <span className="text-xs font-bold text-mint">↑ 4% vs last term</span>
                    </div>
                  </div>
                  <div className="bg-white border-[2px] border-ink rounded-xl p-5 shadow-[3px_3px_0_0_#1A1A1A]">
                    <div className="flex justify-between items-center mb-3">
                      <p className="font-display font-bold text-xs uppercase tracking-wider text-ink/60">Pending Grading</p>
                      <Clock className="text-bubble" size={18} />
                    </div>
                    <div className="flex items-baseline gap-2">
                      <p className="font-display font-black text-4xl">12</p>
                      <span className="text-xs font-bold text-bubble">Requires attention</span>
                    </div>
                  </div>
                </div>

                {/* Chart + Topic Mastery */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">
                  <div className="md:col-span-2 bg-white border-[2px] border-ink rounded-xl p-5 shadow-[3px_3px_0_0_#1A1A1A]">
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="font-display font-black text-xl">Performance Trends</h3>
                      <select className="border-[2px] border-ink rounded-lg text-xs font-bold px-2 py-1 focus:outline-none">
                        <option>Last 5 Weeks</option>
                        <option>Last Term</option>
                      </select>
                    </div>
                    <div className="flex items-end justify-between h-48 gap-4 pt-4 border-b-[2px] border-ink">
                      <div className="bg-cobalt/80 border-[2px] border-ink rounded-t-md w-full h-[60%] shadow-[2px_2px_0_0_#1A1A1A]"></div>
                      <div className="bg-bubble/80 border-[2px] border-ink rounded-t-md w-full h-[40%] shadow-[2px_2px_0_0_#1A1A1A]"></div>
                      <div className="bg-lemon/80 border-[2px] border-ink rounded-t-md w-full h-[80%] shadow-[2px_2px_0_0_#1A1A1A]"></div>
                      <div className="bg-mint/80 border-[2px] border-ink rounded-t-md w-full h-[55%] shadow-[2px_2px_0_0_#1A1A1A]"></div>
                      <div className="bg-tang/80 border-[2px] border-ink rounded-t-md w-full h-[90%] shadow-[2px_2px_0_0_#1A1A1A]"></div>
                    </div>
                    <div className="flex justify-between mt-2 font-bold text-xs text-ink/60">
                      <span>WK 1</span><span>WK 2</span><span>WK 3</span><span>WK 4</span><span>WK 5</span>
                    </div>
                  </div>

                  <div className="bg-white border-[2px] border-ink rounded-xl p-5 shadow-[3px_3px_0_0_#1A1A1A]">
                    <h3 className="font-display font-black text-xl mb-4">Curriculum Mastery</h3>
                    <div className="space-y-4">
                      <div>
                        <div className="flex justify-between font-bold text-xs mb-1">
                          <span>Advanced Algebra</span><span>85%</span>
                        </div>
                        <div className="w-full bg-paper border-[1px] border-ink rounded-full h-3 overflow-hidden">
                          <div className="bg-mint h-full border-r-[1px] border-ink" style={{ width: '85%' }}></div>
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between font-bold text-xs mb-1">
                          <span>Trigonometry</span><span>62%</span>
                        </div>
                        <div className="w-full bg-paper border-[1px] border-ink rounded-full h-3 overflow-hidden">
                          <div className="bg-lemon h-full border-r-[1px] border-ink" style={{ width: '62%' }}></div>
                        </div>
                      </div>
                    </div>
                    <button className="w-full mt-4 text-xs font-bold text-cobalt border-b border-dashed border-cobalt inline-block text-center cursor-pointer">View Full Curriculum</button>
                  </div>
                </div>
              </>
            )}

            {activeTab === 'assessments' && (
              <div className="bg-white border-[2px] border-ink rounded-xl p-6 shadow-[3px_3px_0_0_#1A1A1A]">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="font-display font-black text-2xl">Assessments Bank</h3>
                  {!isCreatingTest && (
                    <button 
                      onClick={() => setIsCreatingTest(true)}
                      className="bg-lemon font-display font-extrabold text-sm px-4 py-2 border-[2px] border-ink rounded-lg shadow-[2px_2px_0_0_#1A1A1A] hover:translate-x-[-1px] hover:translate-y-[-1px] hover:shadow-[3px_3px_0_0_#1A1A1A] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all flex items-center gap-2 cursor-pointer"
                    >
                      <Plus size={16} /> Create Test
                    </button>
                  )}
                </div>

                {isCreatingTest ? (
                  // Create Test Form
                  <div className="border-[2px] border-ink rounded-lg p-5 bg-paper space-y-5">
                    <div className="flex justify-between items-center">
                      <h4 className="font-display font-bold text-lg">Create New Test</h4>
                      <button onClick={() => setIsCreatingTest(false)} className="text-xs font-bold text-ink/60 border-b border-ink/60 border-dashed cursor-pointer">Cancel</button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="font-display font-bold text-xs block mb-1">Test Title</label>
                        <input type="text" placeholder="e.g., Algebra Quiz 1" className="w-full p-2 border-[2px] border-ink rounded-lg text-sm focus:outline-none focus:shadow-[2px_2px_0_0_#1A1A1A]" />
                      </div>
                      <div>
                        <label className="font-display font-bold text-xs block mb-1">Time Limit (minutes)</label>
                        <input type="number" placeholder="30" className="w-full p-2 border-[2px] border-ink rounded-lg text-sm focus:outline-none focus:shadow-[2px_2px_0_0_#1A1A1A]" />
                      </div>
                    </div>

                    {/* Questions Area */}
                    <div className="space-y-4">
                      <label className="font-display font-bold text-xs block">Questions</label>
                      
                      {testQuestions.map((q, idx) => (
                        <div key={idx} className="bg-white border-[2px] border-ink rounded-lg p-4 space-y-3 relative">
                          <button 
                            onClick={() => setTestQuestions(testQuestions.filter((_, i) => i !== idx))}
                            className="absolute top-2 right-2 text-bubble hover:text-red-700 cursor-pointer"
                          >
                            <Trash2 size={16} />
                          </button>
                          
                          <div>
                            <label className="font-bold text-xs text-ink/60">Question {idx + 1}</label>
                            <input type="text" placeholder="Enter question text..." className="w-full p-2 border-[1.5px] border-ink rounded-lg text-sm focus:outline-none focus:shadow-[1px_1px_0_0_#1A1A1A]" />
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {q.options.map((_, optIdx) => (
                              <div key={optIdx} className="flex items-center gap-2">
                                <input type="radio" name={`correct-${idx}`} checked={q.correct === optIdx} onChange={() => {
                                  const newQs = [...testQuestions];
                                  newQs[idx].correct = optIdx;
                                  setTestQuestions(newQs);
                                }} />
                                <input type="text" placeholder={`Option ${optIdx + 1}`} className="w-full p-1.5 border-[1.5px] border-ink rounded-lg text-xs focus:outline-none focus:shadow-[1px_1px_0_0_#1A1A1A]" />
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}

                      <button 
                        onClick={() => setTestQuestions([...testQuestions, { question: '', options: ['', '', '', ''], correct: 0 }])}
                        className="w-full border-[2px] border-dashed border-ink p-3 rounded-lg text-sm font-bold text-ink/60 hover:bg-white transition-colors cursor-pointer flex items-center justify-center gap-2"
                      >
                        <Plus size={16} /> Add Another Question
                      </button>
                    </div>

                    <div className="flex justify-end gap-3 pt-2">
                      <button onClick={() => setIsCreatingTest(false)} className="bg-white font-display font-extrabold text-sm px-4 py-2 border-[2px] border-ink rounded-lg shadow-[2px_2px_0_0_#1A1A1A] cursor-pointer">Save Draft</button>
                      <button onClick={() => setIsCreatingTest(false)} className="bg-mint font-display font-extrabold text-sm px-4 py-2 border-[2px] border-ink rounded-lg shadow-[2px_2px_0_0_#1A1A1A] hover:translate-x-[-1px] hover:translate-y-[-1px] hover:shadow-[3px_3px_0_0_#1A1A1A] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none transition-all cursor-pointer">Publish Test</button>
                    </div>
                  </div>
                ) : (
                  // Assessments List
                  <div className="space-y-3">
                    <div className="border-[2px] border-ink rounded-lg p-4 flex justify-between items-center bg-paper">
                      <div>
                        <p className="font-display font-bold text-lg">Linear Equations Midterm</p>
                        <p className="text-xs font-bold text-ink/50">Class 10 • 45 mins • Created 1 week ago</p>
                      </div>
                      <span className="bg-mint font-bold text-xs px-2 py-1 border-[1.5px] border-ink rounded-full">ACTIVE</span>
                    </div>
                    <div className="border-[2px] border-ink rounded-lg p-4 flex justify-between items-center bg-paper">
                      <div>
                        <p className="font-display font-bold text-lg">Pythagorean Theorem Quiz</p>
                        <p className="text-xs font-bold text-ink/50">Class 9 • 30 mins • Scheduled</p>
                      </div>
                      <span className="bg-lemon font-bold text-xs px-2 py-1 border-[1.5px] border-ink rounded-full">SCHEDULED</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'community' && (
              <div className="bg-white border-[2px] border-ink rounded-xl p-6 shadow-[3px_3px_0_0_#1A1A1A]">
                <h3 className="font-display font-black text-2xl mb-6">Student Roster</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between border-[2px] border-ink p-3 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-paper border-[1.5px] border-ink rounded-full flex items-center justify-center font-bold text-xs">AM</div>
                      <p className="font-bold text-sm">Alex Murphy</p>
                    </div>
                    <p className="text-xs font-bold text-mint">Top Performer</p>
                  </div>
                </div>
              </div>
            )}

            {(activeTab === 'resources' || activeTab === 'settings') && (
              <div className="bg-white border-[2px] border-ink rounded-xl p-6 shadow-[3px_3px_0_0_#1A1A1A] text-center py-12">
                <p className="font-accent text-3xl mb-2">Coming Soon!</p>
                <p className="font-bold text-sm text-ink/60">This section is currently under development.</p>
              </div>
            )}
          </main>
        </div>
      </div>
    )
  }

  // Student Dashboard View
  const StudentView = () => {
    const [activeTab, setActiveTab] = useState('dashboard')

    return (
      <div className="min-h-screen bg-paper flex">
        <Sidebar role="student" activeTab={activeTab} setActiveTab={setActiveTab} />
        
        <div className="flex-grow flex flex-col">
          {/* Top Bar */}
          <div className="bg-white border-b-[2px] border-ink px-6 py-3 flex justify-between items-center">
            <div className="relative hidden sm:block">
              <Search size={16} className="absolute left-3 top-2.5 text-ink/40" />
              <input type="text" placeholder="Search quests..." className="pl-10 pr-4 py-1.5 border-[2px] border-ink rounded-lg text-sm focus:outline-none focus:shadow-[2px_2px_0_0_#1A1A1A]" />
            </div>
            <div className="flex items-center gap-3">
              <div className="border-[2px] border-ink rounded-lg p-0.5 flex gap-0.5 text-xs font-bold bg-paper">
                <button onClick={() => setStudentGrade(6)} className={`px-2 py-0.5 rounded-md cursor-pointer ${studentGrade < 9 ? 'bg-lemon' : 'bg-transparent'}`}>Class &lt; 9</button>
                <button onClick={() => setStudentGrade(10)} className={`px-2 py-0.5 rounded-md cursor-pointer ${studentGrade >= 9 ? 'bg-lemon' : 'bg-transparent'}`}>Class ≥ 9</button>
              </div>
              <button className="relative p-1.5 border-[2px] border-ink rounded-lg hover:bg-paper cursor-pointer">
                <Bell size={18} />
              </button>
            </div>
          </div>

          {/* Content Based on Tab */}
          <main className="p-6 flex-grow">
            {activeTab === 'dashboard' && (
              studentGrade >= 9 ? (
                // Mature Dashboard
                <>
                  <div className="mb-6">
                    <h2 className="font-display font-black text-3xl tracking-tight">Academic Overview</h2>
                    <p className="text-sm font-bold text-ink/60">Welcome back, Student • Grade 10</p>
                  </div>

                  {/* Stat Tiles */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-5 mb-6">
                    <div className="bg-white border-[2px] border-ink rounded-xl p-5 shadow-[3px_3px_0_0_#1A1A1A]">
                      <div className="flex justify-between items-center mb-3">
                        <p className="font-display font-bold text-xs uppercase tracking-wider text-ink/60">Study Streak</p>
                        <Flame className="text-tang" size={18} fill="orange" />
                      </div>
                      <p className="font-display font-black text-4xl">5 Days</p>
                    </div>
                    <div className="bg-white border-[2px] border-ink rounded-xl p-5 shadow-[3px_3px_0_0_#1A1A1A]">
                      <div className="flex justify-between items-center mb-3">
                        <p className="font-display font-bold text-xs uppercase tracking-wider text-ink/60">Total Points</p>
                        <Star className="text-lemon" size={18} fill="yellow" />
                      </div>
                      <p className="font-display font-black text-4xl">1,200</p>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="bg-white border-[2px] border-ink rounded-xl p-5 mb-6 shadow-[3px_3px_0_0_#1A1A1A]">
                    <div className="flex justify-between font-bold text-sm mb-2">
                      <span>Overall Course Proficiency</span>
                      <span className="text-cobalt">80%</span>
                    </div>
                    <div className="w-full bg-paper border-[1px] border-ink rounded-full h-4 overflow-hidden">
                      <div className="bg-mint h-full border-r-[1px] border-ink" style={{ width: '80%' }}></div>
                    </div>
                  </div>

                  {/* Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    <div className="md:col-span-2 space-y-5">
                      <div className="bg-white border-[2px] border-ink rounded-xl p-5 shadow-[3px_3px_0_0_#1A1A1A]">
                        <h3 className="font-display font-black text-xl mb-4">Pending Assessments</h3>
                        <div className="border-[2px] border-ink rounded-lg p-3 flex justify-between items-center bg-paper hover:bg-white transition-colors">
                          <div>
                            <p className="font-display font-bold text-base">Math Pop Quiz</p>
                            <p className="text-xs font-bold text-ink/50">10 Questions • 15 mins</p>
                          </div>
                          <button className="bg-mint font-display font-extrabold text-xs px-4 py-1.5 border-[2px] border-ink rounded-lg shadow-[2px_2px_0_0_#1A1A1A] cursor-pointer">Start Test</button>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-5">
                      <div className="bg-white border-[2px] border-ink rounded-xl p-5 shadow-[3px_3px_0_0_#1A1A1A]">
                        <h3 className="font-display font-black text-xl mb-4">Study Material</h3>
                        <div className="flex items-center gap-2 p-1.5 hover:bg-paper rounded-md transition-colors cursor-pointer">
                          <FileText className="text-cobalt" size={16} />
                          <div>
                            <p className="font-bold text-xs">Advanced Algebra PDF</p>
                            <p className="text-[10px] font-bold text-ink/40">Chapter 4 • 2.4 MB</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                // Playful Dashboard
                <>
                  <div className="bg-bubble border-[2px] border-ink rounded-xl p-5 mb-6 shadow-[3px_3px_0_0_#1A1A1A]">
                    <p className="font-accent text-2xl text-white mb-1">Hey there, hero —</p>
                    <h1 className="font-display font-black text-4xl text-white tracking-tight">Ready for your next quest?</h1>
                  </div>

                  {/* Stat Tiles */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-5 mb-6">
                    <div className="bg-white border-[2px] border-ink rounded-xl p-5 shadow-[3px_3px_0_0_#1A1A1A]">
                      <div className="flex justify-between items-center mb-3">
                        <p className="font-display font-bold text-xs uppercase tracking-wider text-ink/60">Streak</p>
                        <Flame className="text-tang" size={18} fill="orange" />
                      </div>
                      <p className="font-display font-black text-4xl">5</p>
                    </div>
                  </div>

                  {/* Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    <div className="md:col-span-2 space-y-5">
                      <div className="bg-white border-[2px] border-ink rounded-xl p-5 shadow-[3px_3px_0_0_#1A1A1A]">
                        <h3 className="font-display font-black text-xl mb-4">Available Quests</h3>
                        <div className="border-[2px] border-ink rounded-lg p-3 flex justify-between items-center bg-paper hover:bg-white transition-colors">
                          <div>
                            <p className="font-display font-bold text-base">Math Pop Quiz</p>
                            <p className="text-xs font-bold text-ink/50">10 Questions • 15 mins</p>
                          </div>
                          <button className="bg-mint font-display font-extrabold text-xs px-3 py-1.5 border-[2px] border-ink rounded-lg shadow-[2px_2px_0_0_#1A1A1A] cursor-pointer">Start</button>
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )
            )}

            {activeTab === 'assessments' && (
              <div className="bg-white border-[2px] border-ink rounded-xl p-6 shadow-[3px_3px_0_0_#1A1A1A]">
                <h3 className="font-display font-black text-2xl mb-6">My Assessments</h3>
                <div className="space-y-3">
                  <div className="border-[2px] border-ink rounded-lg p-4 flex justify-between items-center">
                    <div>
                      <p className="font-display font-bold text-lg">Linear Equations Midterm</p>
                      <p className="text-xs font-bold text-ink/50">Completed 2 days ago</p>
                    </div>
                    <span className="font-display font-black text-xl text-mint">92%</span>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'community' && (
              <div className="bg-white border-[2px] border-ink rounded-xl p-6 shadow-[3px_3px_0_0_#1A1A1A]">
                <h3 className="font-display font-black text-2xl mb-6">Class Leaderboard</h3>
                <div className="space-y-3">
                  <div className="flex items-center gap-3 font-bold text-sm bg-paper p-3 rounded-lg border-[2px] border-ink">
                    <span className="w-6 h-6 bg-lemon rounded-full flex items-center justify-center border-[1.5px] border-ink text-xs">4</span>
                    <span>You (Alex)</span>
                    <span className="ml-auto">1200 pts</span>
                  </div>
                </div>
              </div>
            )}

            {(activeTab === 'resources' || activeTab === 'settings') && (
              <div className="bg-white border-[2px] border-ink rounded-xl p-6 shadow-[3px_3px_0_0_#1A1A1A] text-center py-12">
                <p className="font-accent text-3xl mb-2">Coming Soon!</p>
                <p className="font-bold text-sm text-ink/60">This section is currently under development.</p>
              </div>
            )}
          </main>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-cream font-sans text-ink relative overflow-hidden">
      {view === 'landing' && <LandingView />}
      {view === 'teacher' && <TeacherView />}
      {view === 'student' && <StudentView />}
      {view === 'contact' && <ContactView />}
      {view === 'login' && <LoginView />}
      {view === 'signup' && <SignupView />}
    </div>
  )
}

export default App
